"""
Apple Container Integration - Native macOS sandboxed execution.

Provides isolated execution environments using Apple's container technology
for secure code execution without needing to offload to Linux nodes.

Requirements:
- macOS 26+ (Tahoe or later)
- Apple Container installed: https://github.com/apple/container
- Container service running: `container system start`

Security Note:
- Uses asyncio.create_subprocess_exec (not shell=True) to prevent injection
- All user input passed as discrete arguments, never interpolated into commands
- Container provides additional isolation layer
"""

import asyncio
import json
import logging
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Any
from enum import Enum

logger = logging.getLogger(__name__)


class ContainerStatus(Enum):
    """Container system status."""
    NOT_INSTALLED = "not_installed"
    NOT_RUNNING = "not_running"
    RUNNING = "running"
    ERROR = "error"


@dataclass
class ContainerResult:
    """Result from container execution."""
    success: bool
    exit_code: int
    stdout: str
    stderr: str
    execution_time: float = 0.0
    container_id: Optional[str] = None

    def to_observation(self) -> str:
        """Format as observation string."""
        if self.success:
            return f"Container execution succeeded (exit {self.exit_code}):\n{self.stdout[:2000]}"
        else:
            return f"Container execution failed (exit {self.exit_code}):\n{self.stderr[:1000]}"


@dataclass
class ContainerConfig:
    """Configuration for container execution."""
    image: str = "alpine:latest"
    workdir: str = "/workspace"
    timeout: int = 300
    memory_limit: str = "512m"
    cpu_limit: float = 1.0
    network: bool = False
    mounts: list[tuple[str, str]] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)


class AppleContainerSandbox:
    """
    Sandboxed execution using Apple Container.

    Uses asyncio.create_subprocess_exec for safe argument passing.
    """

    DEFAULT_IMAGE = "alpine:latest"
    PYTHON_IMAGE = "python:3.11-alpine"
    NODE_IMAGE = "node:20-alpine"

    def __init__(
        self,
        default_image: str = DEFAULT_IMAGE,
        workspace: Path = None,
        auto_pull: bool = True
    ):
        self.default_image = default_image
        self.workspace = workspace or Path("/tmp/prometheus-sandbox")
        self.auto_pull = auto_pull
        self._container_path = self._find_container_binary()
        self._pulled_images: set[str] = set()

    def _find_container_binary(self) -> Optional[Path]:
        """Find the container binary."""
        locations = [
            "/usr/local/bin/container",
            "/opt/homebrew/bin/container",
        ]

        which_result = shutil.which("container")
        if which_result:
            locations.insert(0, which_result)

        for loc in locations:
            if loc and Path(loc).exists():
                return Path(loc)
        return None

    def is_available(self) -> bool:
        """Check if Apple Container is available and running."""
        return self.get_status() == ContainerStatus.RUNNING

    def get_status(self) -> ContainerStatus:
        """Get current container system status."""
        if not self._container_path:
            return ContainerStatus.NOT_INSTALLED

        try:
            import subprocess as sp
            result = sp.run(
                [str(self._container_path), "system", "status"],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0 and "is running" in result.stdout:
                return ContainerStatus.RUNNING
            elif "not running" in result.stdout.lower() or "not running" in result.stderr.lower():
                return ContainerStatus.NOT_RUNNING
            else:
                return ContainerStatus.ERROR

        except Exception as e:
            logger.warning(f"Container status check failed: {e}")
            return ContainerStatus.ERROR

    async def pull_image(self, image: str) -> bool:
        """Pull a container image using safe argument passing."""
        if image in self._pulled_images:
            return True

        if not self._container_path:
            return False

        logger.info(f"Pulling image: {image}")

        try:
            # Safe: arguments passed as list, no shell interpolation
            proc = await asyncio.create_subprocess_exec(
                str(self._container_path), "image", "pull", image,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=300)

            if proc.returncode == 0:
                self._pulled_images.add(image)
                logger.info(f"Successfully pulled {image}")
                return True
            else:
                logger.error(f"Failed to pull {image}: {stderr.decode()}")
                return False

        except asyncio.TimeoutError:
            logger.error(f"Timeout pulling image {image}")
            return False

    async def execute(
        self,
        command: str,
        config: ContainerConfig = None,
        image: str = None
    ) -> ContainerResult:
        """
        Execute command in isolated container.

        Security: Command runs INSIDE container, isolated from host.
        The container binary itself is called with safe argument passing.
        """
        import time

        if not self.is_available():
            return ContainerResult(
                success=False, exit_code=-1, stdout="",
                stderr="Apple Container not available. Run: container system start"
            )

        config = config or ContainerConfig()
        image = image or config.image or self.default_image

        if self.auto_pull and not await self.pull_image(image):
            return ContainerResult(
                success=False, exit_code=-1, stdout="",
                stderr=f"Failed to pull image: {image}"
            )

        self.workspace.mkdir(parents=True, exist_ok=True)

        # Build argument list (safe - no shell interpolation)
        args = [
            str(self._container_path), "run", "--rm",
            "-w", config.workdir,
        ]

        if config.memory_limit:
            args.extend(["--memory", config.memory_limit])

        args.extend(["-v", f"{self.workspace}:{config.workdir}"])

        for host_path, container_path in config.mounts:
            args.extend(["-v", f"{host_path}:{container_path}"])

        for key, value in config.env.items():
            args.extend(["-e", f"{key}={value}"])

        if not config.network:
            args.extend(["--network", "none"])

        # Image and command (command runs inside container)
        args.append(image)
        args.extend(["sh", "-c", command])

        logger.info(f"Running in container: {command[:100]}...")
        start_time = time.time()

        try:
            # Safe: using create_subprocess_exec with argument list
            proc = await asyncio.create_subprocess_exec(
                *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=config.timeout
            )

            return ContainerResult(
                success=proc.returncode == 0,
                exit_code=proc.returncode,
                stdout=stdout.decode(errors="replace"),
                stderr=stderr.decode(errors="replace"),
                execution_time=time.time() - start_time
            )

        except asyncio.TimeoutError:
            return ContainerResult(
                success=False, exit_code=-1, stdout="",
                stderr=f"Execution timed out after {config.timeout}s",
                execution_time=config.timeout
            )

    async def execute_python(self, code: str, timeout: int = 60) -> ContainerResult:
        """Execute Python code in isolated container."""
        code_file = self.workspace / "script.py"
        code_file.parent.mkdir(parents=True, exist_ok=True)
        code_file.write_text(code)

        config = ContainerConfig(image=self.PYTHON_IMAGE, timeout=timeout)
        return await self.execute("python /workspace/script.py", config)

    def get_system_info(self) -> dict:
        """Get container system information."""
        if not self._container_path:
            return {"status": "not_installed"}

        import subprocess as sp
        try:
            result = sp.run(
                [str(self._container_path), "system", "status"],
                capture_output=True, text=True, timeout=10
            )
            is_running = result.returncode == 0 and "is running" in result.stdout
            return {
                "status": "running" if is_running else "stopped",
                "output": result.stdout,
                "binary_path": str(self._container_path)
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}


_sandbox: Optional[AppleContainerSandbox] = None


def get_sandbox(workspace: Path = None) -> AppleContainerSandbox:
    """Get or create global sandbox instance."""
    global _sandbox
    if _sandbox is None:
        _sandbox = AppleContainerSandbox(workspace=workspace or Path("/tmp/prometheus-sandbox"))
    return _sandbox


async def _test_sandbox():
    """Test Apple Container sandbox."""
    sandbox = AppleContainerSandbox()
    print(f"Container binary: {sandbox._container_path}")
    print(f"Status: {sandbox.get_status().value}")

    if not sandbox.is_available():
        print("\nApple Container not available.")
        print("Install: https://github.com/apple/container/releases")
        print("Start: container system start")
        return

    print("\nRunning test in container...")
    result = await sandbox.execute("echo 'Hello from Apple Container!' && uname -a")
    print(f"Success: {result.success}")
    print(f"Output:\n{result.stdout}")


if __name__ == "__main__":
    asyncio.run(_test_sandbox())
