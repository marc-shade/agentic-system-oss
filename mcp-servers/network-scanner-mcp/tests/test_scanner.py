"""Tests for network_scanner_mcp.scanner module."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from network_scanner_mcp.scanner import (
    PortScanResult,
    DeviceScanResult,
    _identify_service,
    COMMON_PORTS,
    SERVICE_PORTS,
)


class TestPortScanResult:
    """Tests for PortScanResult dataclass."""

    def test_creation(self):
        """Test creating a PortScanResult."""
        result = PortScanResult(
            port=80,
            state="open",
            service="http",
            banner="nginx/1.18",
            response_time_ms=5.2
        )

        assert result.port == 80
        assert result.state == "open"
        assert result.service == "http"
        assert result.banner == "nginx/1.18"
        assert result.response_time_ms == 5.2

    def test_default_values(self):
        """Test default values for PortScanResult."""
        result = PortScanResult(port=22, state="closed")

        assert result.service == "unknown"
        assert result.banner is None
        assert result.response_time_ms is None


class TestDeviceScanResult:
    """Tests for DeviceScanResult dataclass."""

    def test_creation(self):
        """Test creating a DeviceScanResult."""
        result = DeviceScanResult(
            ip="198.51.100.100",
            mac="AA:BB:CC:DD:EE:FF",
            vendor="Test Vendor",
            scan_time="2024-01-15T12:00:00"
        )

        assert result.ip == "198.51.100.100"
        assert result.mac == "AA:BB:CC:DD:EE:FF"
        assert result.vendor == "Test Vendor"
        assert result.hostname is None
        assert result.ports == []
        assert result.services == []
        assert result.is_reachable is True

    def test_to_dict(self):
        """Test converting DeviceScanResult to dictionary."""
        result = DeviceScanResult(
            ip="198.51.100.100",
            mac="AA:BB:CC:DD:EE:FF",
            vendor="Test Vendor",
            scan_time="2024-01-15T12:00:00",
            hostname="test-host",
            ports=[PortScanResult(port=22, state="open", service="ssh")],
            services=["ssh"],
        )

        d = result.to_dict()

        assert d["ip"] == "198.51.100.100"
        assert d["mac"] == "AA:BB:CC:DD:EE:FF"
        assert d["hostname"] == "test-host"
        assert len(d["ports"]) == 1
        assert d["ports"][0]["port"] == 22
        assert d["services"] == ["ssh"]


class TestIdentifyService:
    """Tests for _identify_service function."""

    def test_http_banner(self):
        """Test identifying HTTP from banner."""
        assert _identify_service(80, "HTTP/1.1 200 OK") == "http"

    def test_nginx_banner(self):
        """Test identifying nginx from banner."""
        assert _identify_service(80, "nginx/1.18.0") == "nginx"

    def test_apache_banner(self):
        """Test identifying apache from banner."""
        assert _identify_service(80, "Apache/2.4.41") == "apache"

    def test_ssh_banner(self):
        """Test identifying SSH from banner."""
        assert _identify_service(22, "SSH-2.0-OpenSSH_8.4") == "ssh"

    def test_mysql_banner(self):
        """Test identifying MySQL from banner."""
        assert _identify_service(3306, "5.7.35-MySQL Community Server") == "mysql"

    def test_redis_banner(self):
        """Test identifying Redis from banner."""
        assert _identify_service(6379, "REDIS ver") == "redis"

    def test_unknown_banner(self):
        """Test fallback to port-based identification."""
        assert _identify_service(22, "something unknown") == SERVICE_PORTS[22]

    def test_unknown_port_and_banner(self):
        """Test completely unknown service."""
        assert _identify_service(99999, "unknown") == "unknown"


class TestServicePorts:
    """Tests for SERVICE_PORTS constant."""

    def test_common_ports_defined(self):
        """Test that common ports are defined."""
        assert 22 in SERVICE_PORTS  # SSH
        assert 80 in SERVICE_PORTS  # HTTP
        assert 443 in SERVICE_PORTS  # HTTPS
        assert 3306 in SERVICE_PORTS  # MySQL
        assert 5432 in SERVICE_PORTS  # PostgreSQL

    def test_service_names(self):
        """Test service names for common ports."""
        assert SERVICE_PORTS[22] == "ssh"
        assert SERVICE_PORTS[80] == "http"
        assert SERVICE_PORTS[443] == "https"
        assert SERVICE_PORTS[3306] == "mysql"


class TestCommonPorts:
    """Tests for COMMON_PORTS constant."""

    def test_contains_standard_ports(self):
        """Test that COMMON_PORTS includes standard ports."""
        assert 22 in COMMON_PORTS  # SSH
        assert 80 in COMMON_PORTS  # HTTP
        assert 443 in COMMON_PORTS  # HTTPS

    def test_reasonable_size(self):
        """Test that COMMON_PORTS is a reasonable size for quick scans."""
        assert len(COMMON_PORTS) > 5
        assert len(COMMON_PORTS) < 50


class TestArpScan:
    """Tests for arp_scan function (mocked)."""

    @pytest.mark.asyncio
    async def test_arp_scan_success(self):
        """Test successful ARP scan with mocked subprocess."""
        from network_scanner_mcp.scanner import arp_scan

        mock_output = b"198.51.100.1\taa:bb:cc:dd:ee:ff\tTest Vendor\n198.51.100.2\t11:22:33:44:55:66\tAnother Vendor\n"

        with patch('asyncio.create_subprocess_exec') as mock_exec:
            mock_process = AsyncMock()
            mock_process.returncode = 0
            mock_process.communicate = AsyncMock(return_value=(mock_output, b""))
            mock_exec.return_value = mock_process

            devices = await arp_scan(interface="eth0")

            assert len(devices) == 2
            assert devices[0]["ip"] == "198.51.100.1"
            assert devices[0]["mac"] == "AA:BB:CC:DD:EE:FF"
            assert devices[1]["ip"] == "198.51.100.2"

    @pytest.mark.asyncio
    async def test_arp_scan_no_devices(self):
        """Test ARP scan with no devices found."""
        from network_scanner_mcp.scanner import arp_scan

        with patch('asyncio.create_subprocess_exec') as mock_exec:
            mock_process = AsyncMock()
            mock_process.returncode = 0
            mock_process.communicate = AsyncMock(return_value=(b"", b""))
            mock_exec.return_value = mock_process

            devices = await arp_scan(interface="eth0")

            assert devices == []

    @pytest.mark.asyncio
    async def test_arp_scan_failure(self):
        """Test ARP scan failure returns empty list."""
        from network_scanner_mcp.scanner import arp_scan

        with patch('asyncio.create_subprocess_exec') as mock_exec:
            mock_process = AsyncMock()
            mock_process.returncode = 1
            mock_process.communicate = AsyncMock(return_value=(b"", b"Error"))
            mock_exec.return_value = mock_process

            devices = await arp_scan(interface="eth0")

            assert devices == []


class TestScanPort:
    """Tests for scan_port function (mocked)."""

    @pytest.mark.asyncio
    async def test_scan_port_open(self):
        """Test scanning an open port."""
        from network_scanner_mcp.scanner import scan_port

        with patch('asyncio.open_connection') as mock_conn:
            mock_reader = AsyncMock()
            mock_reader.read = AsyncMock(return_value=b"SSH-2.0-OpenSSH")
            mock_writer = AsyncMock()
            mock_writer.close = MagicMock()
            mock_writer.wait_closed = AsyncMock()
            mock_conn.return_value = (mock_reader, mock_writer)

            result = await scan_port("198.51.100.1", 22, timeout=1.0)

            assert result.port == 22
            assert result.state == "open"

    @pytest.mark.asyncio
    async def test_scan_port_closed(self):
        """Test scanning a closed port."""
        from network_scanner_mcp.scanner import scan_port

        with patch('asyncio.open_connection') as mock_conn:
            mock_conn.side_effect = ConnectionRefusedError()

            result = await scan_port("198.51.100.1", 12345, timeout=1.0)

            assert result.port == 12345
            assert result.state == "closed"

    @pytest.mark.asyncio
    async def test_scan_port_filtered(self):
        """Test scanning a filtered port (timeout)."""
        from network_scanner_mcp.scanner import scan_port

        with patch('asyncio.open_connection') as mock_conn:
            mock_conn.side_effect = asyncio.TimeoutError()

            result = await scan_port("198.51.100.1", 80, timeout=0.1)

            assert result.port == 80
            assert result.state == "filtered"


class TestPingHost:
    """Tests for ping_host function (mocked)."""

    @pytest.mark.asyncio
    async def test_ping_host_up(self):
        """Test pinging a reachable host."""
        from network_scanner_mcp.scanner import ping_host

        mock_output = b"PING 198.51.100.1 (198.51.100.1) 56(84) bytes of data.\n64 bytes: icmp_seq=1 ttl=64 time=0.5 ms\nrtt min/avg/max/mdev = 0.5/0.5/0.5/0.0 ms\n"

        with patch('asyncio.create_subprocess_exec') as mock_exec:
            mock_process = AsyncMock()
            mock_process.returncode = 0
            mock_process.communicate = AsyncMock(return_value=(mock_output, b""))
            mock_exec.return_value = mock_process

            is_up, latency = await ping_host("198.51.100.1")

            assert is_up is True

    @pytest.mark.asyncio
    async def test_ping_host_down(self):
        """Test pinging an unreachable host."""
        from network_scanner_mcp.scanner import ping_host

        with patch('asyncio.create_subprocess_exec') as mock_exec:
            mock_process = AsyncMock()
            mock_process.returncode = 1
            mock_process.communicate = AsyncMock(return_value=(b"", b""))
            mock_exec.return_value = mock_process

            is_up, latency = await ping_host("198.51.100.99")

            assert is_up is False
            assert latency is None


class TestResolveHostname:
    """Tests for resolve_hostname function (mocked)."""

    @pytest.mark.asyncio
    async def test_resolve_hostname_success(self):
        """Test successful hostname resolution."""
        from network_scanner_mcp.scanner import resolve_hostname

        with patch('socket.gethostbyaddr') as mock_lookup:
            mock_lookup.return_value = ("test-host.local", [], ["198.51.100.1"])

            hostname = await resolve_hostname("198.51.100.1")

            assert hostname == "test-host.local"

    @pytest.mark.asyncio
    async def test_resolve_hostname_failure(self):
        """Test failed hostname resolution."""
        from network_scanner_mcp.scanner import resolve_hostname
        import socket

        with patch('socket.gethostbyaddr') as mock_lookup:
            mock_lookup.side_effect = socket.herror()

            hostname = await resolve_hostname("198.51.100.99")

            assert hostname is None
