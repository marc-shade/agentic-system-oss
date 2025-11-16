"""
Cross-Compilation Workflow Skill

Build binaries for multiple architectures and platforms
using the Builder node's toolchain.

Builder Node Skill - Version 1.0
"""

def cross_compile_rust(
    project_dir: str,
    targets: list = ["x86_64-unknown-linux-gnu", "aarch64-unknown-linux-gnu"],
    release: bool = True,
    strip_symbols: bool = True
) -> dict:
    """
    Cross-compile Rust project for multiple targets.

    Args:
        project_dir: Cargo project directory
        targets: List of Rust target triples
        release: Build with optimizations
        strip_symbols: Strip debug symbols for smaller binaries

    Returns:
        dict: Build results for each target
    """
    import subprocess
    import os
    from pathlib import Path

    results = {"targets": {}, "success": True}

    for target in targets:
        target_result = {
            "success": False,
            "binary_path": None,
            "size_bytes": None
        }

        try:
            # Add target if not installed
            add_target_cmd = ["rustup", "target", "add", target]
            subprocess.run(add_target_cmd, check=True, capture_output=True)

            # Build command
            build_cmd = [
                "cargo", "build",
                "--target", target
            ]

            if release:
                build_cmd.append("--release")

            # Set sccache for distributed caching
            env = os.environ.copy()
            env["RUSTC_WRAPPER"] = "sccache"

            result = subprocess.run(
                build_cmd,
                cwd=project_dir,
                env=env,
                capture_output=True,
                text=True,
                check=True
            )

            # Find binary
            build_type = "release" if release else "debug"
            binary_dir = Path(project_dir) / "target" / target / build_type
            binary = next(binary_dir.glob("*"), None)

            if binary and binary.is_file():
                target_result["binary_path"] = str(binary)
                target_result["size_bytes"] = binary.stat().st_size

                # Strip symbols if requested
                if strip_symbols and release:
                    strip_cmd = ["strip", str(binary)]
                    subprocess.run(strip_cmd, capture_output=True)
                    target_result["size_bytes_stripped"] = binary.stat().st_size

                target_result["success"] = True

        except subprocess.CalledProcessError as e:
            target_result["error"] = e.stderr
            results["success"] = False

        results["targets"][target] = target_result

    return results


def cross_compile_go(
    project_dir: str,
    platforms: list = [("linux", "amd64"), ("linux", "arm64"), ("darwin", "arm64")],
    compress: bool = True
) -> dict:
    """
    Cross-compile Go project for multiple OS/arch combinations.

    Args:
        project_dir: Go project directory
        platforms: List of (GOOS, GOARCH) tuples
        compress: Compress binaries with upx

    Returns:
        dict: Build results for each platform
    """
    import subprocess
    import os
    from pathlib import Path

    results = {"platforms": {}, "success": True}
    project_name = Path(project_dir).name

    for goos, goarch in platforms:
        platform_key = f"{goos}-{goarch}"
        platform_result = {
            "success": False,
            "binary_path": None,
            "size_bytes": None
        }

        try:
            output_name = f"{project_name}-{platform_key}"
            if goos == "windows":
                output_name += ".exe"

            # Build command
            env = os.environ.copy()
            env["GOOS"] = goos
            env["GOARCH"] = goarch
            env["CGO_ENABLED"] = "0"  # Static linking

            build_cmd = [
                "go", "build",
                "-ldflags", "-s -w",  # Strip debug info
                "-o", output_name,
                "."
            ]

            subprocess.run(
                build_cmd,
                cwd=project_dir,
                env=env,
                capture_output=True,
                text=True,
                check=True
            )

            binary_path = Path(project_dir) / output_name
            platform_result["binary_path"] = str(binary_path)
            platform_result["size_bytes"] = binary_path.stat().st_size

            # Compress if requested (only for compatible platforms)
            if compress and goos == "linux":
                compress_cmd = ["upx", "--best", "--lzma", str(binary_path)]
                try:
                    subprocess.run(compress_cmd, capture_output=True, timeout=300)
                    platform_result["size_bytes_compressed"] = binary_path.stat().st_size
                except:
                    pass  # upx might not be available

            platform_result["success"] = True

        except subprocess.CalledProcessError as e:
            platform_result["error"] = e.stderr
            results["success"] = False

        results["platforms"][platform_key] = platform_result

    return results


def build_python_wheels(
    project_dir: str,
    python_versions: list = ["3.12", "3.14"],
    platforms: list = ["manylinux_2_28_x86_64"]
) -> dict:
    """
    Build Python wheel packages for multiple versions and platforms.

    Args:
        project_dir: Python project directory
        python_versions: List of Python versions
        platforms: List of platform tags

    Returns:
        dict: Build results with wheel paths
    """
    import subprocess
    from pathlib import Path

    results = {"wheels": [], "success": True}

    for py_version in python_versions:
        for platform in platforms:
            try:
                # Build wheel
                build_cmd = [
                    f"python{py_version}", "-m", "build",
                    "--wheel",
                    "--outdir", f"/tmp/wheels-{py_version}",
                    project_dir
                ]

                subprocess.run(build_cmd, capture_output=True, text=True, check=True)

                # Find generated wheel
                dist_dir = Path(f"/tmp/wheels-{py_version}")
                wheels = list(dist_dir.glob("*.whl"))

                for wheel in wheels:
                    results["wheels"].append({
                        "python_version": py_version,
                        "platform": platform,
                        "path": str(wheel),
                        "size_bytes": wheel.stat().st_size
                    })

            except subprocess.CalledProcessError as e:
                results["success"] = False
                results["wheels"].append({
                    "python_version": py_version,
                    "platform": platform,
                    "error": e.stderr
                })

    return results


# Example usage
if __name__ == "__main__":
    # Cross-compile Rust for multiple architectures
    rust_result = cross_compile_rust(
        project_dir="/path/to/rust/project",
        targets=["x86_64-unknown-linux-gnu", "aarch64-unknown-linux-gnu"],
        release=True,
        strip_symbols=True
    )

    for target, result in rust_result["targets"].items():
        if result["success"]:
            size_mb = result["size_bytes"] / (1024 * 1024)
            print(f"{target}: {size_mb:.2f} MB")
