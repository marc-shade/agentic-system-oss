"""Pytest configuration and fixtures for cluster-execution-mcp tests."""

import os
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

# Set test environment variables before importing modules
os.environ.setdefault("CLUSTER_SSH_USER", "testuser")
os.environ.setdefault("CLUSTER_SSH_TIMEOUT", "2")
os.environ.setdefault("CLUSTER_CMD_TIMEOUT", "10")


@pytest.fixture
def mock_subprocess():
    """Mock subprocess.run for testing without actual SSH calls."""
    with patch("subprocess.run") as mock_run:
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "test output"
        mock_result.stderr = ""
        mock_run.return_value = mock_result
        yield mock_run


@pytest.fixture
def mock_psutil():
    """Mock psutil for testing without actual system metrics."""
    with patch("psutil.cpu_percent", return_value=25.0), \
         patch("psutil.virtual_memory") as mock_mem, \
         patch("psutil.getloadavg", return_value=(1.5, 1.0, 0.5)):
        mock_mem.return_value = MagicMock(percent=50.0)
        yield


@pytest.fixture
def temp_db():
    """Create temporary database for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_task_queue.db"
        with patch("cluster_execution_mcp.config.get_db_path", return_value=db_path):
            yield db_path


@pytest.fixture
def mock_ssh_success():
    """Mock successful SSH connectivity."""
    with patch("cluster_execution_mcp.router.verify_ssh_connectivity", return_value=True):
        yield


@pytest.fixture
def mock_ssh_failure():
    """Mock failed SSH connectivity."""
    with patch("cluster_execution_mcp.router.verify_ssh_connectivity", return_value=False):
        yield


@pytest.fixture
def clear_ip_cache():
    """Clear IP cache before tests."""
    from cluster_execution_mcp.router import clear_ip_cache
    clear_ip_cache()
    yield
    clear_ip_cache()
