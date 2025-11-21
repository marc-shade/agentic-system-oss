"""
Multi-Stage Docker Build Skill

Optimized multi-stage container builds with layer caching,
security scanning, and minimal final image size.

Builder Node Skill - Version 1.0
"""

def multi_stage_docker_build(
    source_dir: str,
    image_name: str,
    target_stage: str = "production",
    enable_cache: bool = True,
    scan_security: bool = True,
    push_to_registry: bool = False,
    registry_url: str = None
) -> dict:
    """
    Execute optimized multi-stage Docker build.

    Args:
        source_dir: Directory containing Dockerfile
        image_name: Name for the built image
        target_stage: Build target stage (development, testing, production)
        enable_cache: Use build cache for faster builds
        scan_security: Run security scanning on built image
        push_to_registry: Push to container registry
        registry_url: Registry URL for push

    Returns:
        dict: Build results with size, layers, vulnerabilities
    """
    import subprocess
    import json
    from pathlib import Path

    results = {
        "success": False,
        "image_name": image_name,
        "target_stage": target_stage,
        "image_size": None,
        "layers": 0,
        "vulnerabilities": None,
        "build_time": None
    }

    # Build command with Buildah (rootless, OCI-compliant)
    build_cmd = [
        "buildah", "bud",
        "--target", target_stage,
        "--tag", image_name,
        "--layers" if enable_cache else "--no-cache",
        "--format", "oci",
        source_dir
    ]

    # Execute build
    import time
    start = time.time()

    try:
        result = subprocess.run(
            build_cmd,
            capture_output=True,
            text=True,
            check=True
        )

        results["build_time"] = time.time() - start
        results["success"] = True

        # Get image size and layer count
        inspect_cmd = ["podman", "inspect", image_name]
        inspect_result = subprocess.run(
            inspect_cmd,
            capture_output=True,
            text=True,
            check=True
        )

        image_info = json.loads(inspect_result.stdout)[0]
        results["image_size"] = image_info.get("Size", 0)
        results["layers"] = len(image_info.get("RootFS", {}).get("Layers", []))

        # Security scanning if enabled
        if scan_security:
            scan_cmd = ["podman", "run", "--rm",
                       "aquasec/trivy:latest",
                       "image", "--format", "json",
                       image_name]

            try:
                scan_result = subprocess.run(
                    scan_cmd,
                    capture_output=True,
                    text=True,
                    timeout=300
                )

                if scan_result.returncode == 0:
                    scan_data = json.loads(scan_result.stdout)
                    results["vulnerabilities"] = {
                        "critical": sum(1 for v in scan_data.get("Results", [])
                                      for vuln in v.get("Vulnerabilities", [])
                                      if vuln.get("Severity") == "CRITICAL"),
                        "high": sum(1 for v in scan_data.get("Results", [])
                                   for vuln in v.get("Vulnerabilities", [])
                                   if vuln.get("Severity") == "HIGH")
                    }
            except Exception as e:
                results["vulnerabilities"] = {"error": str(e)}

        # Push to registry if requested
        if push_to_registry and registry_url:
            registry_image = f"{registry_url}/{image_name}"
            tag_cmd = ["podman", "tag", image_name, registry_image]
            subprocess.run(tag_cmd, check=True)

            push_cmd = ["podman", "push", registry_image]
            subprocess.run(push_cmd, check=True)
            results["pushed_to"] = registry_image

    except subprocess.CalledProcessError as e:
        results["error"] = e.stderr
    except Exception as e:
        results["error"] = str(e)

    return results


def create_optimized_dockerfile(
    language: str,
    project_type: str,
    output_path: str
) -> str:
    """
    Generate optimized multi-stage Dockerfile template.

    Args:
        language: Programming language (python, rust, go, node)
        project_type: Type (web, cli, library)
        output_path: Where to write Dockerfile

    Returns:
        str: Path to created Dockerfile
    """
    templates = {
        "python": """
# Multi-stage Python 3.14 build
FROM python:3.14-slim AS builder

WORKDIR /build
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

COPY . .
RUN python3.14 -m build

FROM python:3.14-slim AS production

# Security: Run as non-root
RUN useradd -m -u 1000 appuser
WORKDIR /app
USER appuser

# Copy only what's needed
COPY --from=builder /root/.local /home/appuser/.local
COPY --from=builder /build/dist/*.whl /tmp/
RUN pip install --user --no-cache-dir /tmp/*.whl

ENV PATH=/home/appuser/.local/bin:$PATH
CMD ["python3.14", "-m", "myapp"]
""",

        "rust": """
# Multi-stage Rust build
FROM rust:1.91 AS builder

WORKDIR /build
COPY Cargo.toml Cargo.lock ./
COPY src ./src

# Build with optimizations
RUN cargo build --release

FROM debian:bookworm-slim AS production

# Security: Run as non-root
RUN useradd -m -u 1000 appuser
USER appuser
WORKDIR /app

# Copy only the binary
COPY --from=builder /build/target/release/myapp /app/

CMD ["./myapp"]
""",

        "node": """
# Multi-stage Node.js build
FROM node:22-alpine AS builder

WORKDIR /build
COPY package*.json ./
RUN npm ci --only=production

COPY . .
RUN npm run build

FROM node:22-alpine AS production

# Security: Run as non-root
RUN addgroup -g 1000 appuser && adduser -D -u 1000 -G appuser appuser
USER appuser
WORKDIR /app

# Copy only production files
COPY --from=builder /build/node_modules ./node_modules
COPY --from=builder /build/dist ./dist
COPY --from=builder /build/package.json ./

CMD ["node", "dist/index.js"]
"""
    }

    template = templates.get(language, templates["python"])

    with open(output_path, 'w') as f:
        f.write(template)

    return output_path


# Example usage
if __name__ == "__main__":
    # Build a Python project
    result = multi_stage_docker_build(
        source_dir="/path/to/project",
        image_name="myapp:latest",
        target_stage="production",
        enable_cache=True,
        scan_security=True
    )

    print(f"Build {'succeeded' if result['success'] else 'failed'}")
    print(f"Image size: {result['image_size'] / (1024*1024):.2f} MB")
    print(f"Layers: {result['layers']}")
    if result['vulnerabilities']:
        print(f"Security: {result['vulnerabilities']}")
