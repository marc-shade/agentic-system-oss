#!/usr/bin/env python3
"""
Tests for Memory Database Client.

Tests the Unix socket client for concurrent memory-db access.
Uses mocking since actual memory-db service may not be running during tests.

Coverage:
- MemoryClient initialization
- Request/response formatting
- Async and sync method wrappers
- Global client singleton
- Convenience wrapper functions
"""

import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path

# Import the modules under test
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from memory_client import (
    MemoryClient,
    get_client,
    create_entities,
    search_nodes,
    get_memory_status,
    _client
)
import memory_client as memory_client_module


# ============================================================================
# MemoryClient Initialization Tests
# ============================================================================

class TestMemoryClientInit:
    """Tests for MemoryClient initialization."""

    def test_default_socket_path(self):
        """Test default socket path is set correctly."""
        client = MemoryClient()
        assert client.socket_path == "/tmp/memory-db.sock"

    def test_custom_socket_path(self):
        """Test custom socket path is accepted."""
        client = MemoryClient(socket_path="/custom/path.sock")
        assert client.socket_path == "/custom/path.sock"

    def test_socket_path_types(self):
        """Test socket path accepts string."""
        client = MemoryClient(socket_path="/var/run/test.sock")
        assert isinstance(client.socket_path, str)


# ============================================================================
# Request/Response Formatting Tests
# ============================================================================

class TestRequestFormatting:
    """Tests for request/response formatting."""

    @pytest.fixture
    def client(self):
        """Create a MemoryClient instance."""
        return MemoryClient()

    @pytest.mark.asyncio
    async def test_request_format_with_params(self, client):
        """Test request is formatted correctly with params."""
        # Mock the Unix connection
        mock_reader = AsyncMock()
        mock_writer = AsyncMock()

        # Capture the written data
        written_data = []
        mock_writer.write = lambda d: written_data.append(d)
        mock_writer.drain = AsyncMock()
        mock_writer.close = MagicMock()
        mock_writer.wait_closed = AsyncMock()

        # Set up response
        response = {"success": True, "result": "test"}
        mock_reader.read = AsyncMock(side_effect=[
            json.dumps(response).encode(),
            b''  # EOF
        ])

        with patch('asyncio.open_unix_connection', return_value=(mock_reader, mock_writer)):
            result = await client._send_request("test_method", {"key": "value"})

        # Verify request format
        assert len(written_data) == 1
        request = json.loads(written_data[0].decode())
        assert request["method"] == "test_method"
        assert request["params"] == {"key": "value"}

    @pytest.mark.asyncio
    async def test_request_format_without_params(self, client):
        """Test request is formatted correctly without params."""
        mock_reader = AsyncMock()
        mock_writer = AsyncMock()

        written_data = []
        mock_writer.write = lambda d: written_data.append(d)
        mock_writer.drain = AsyncMock()
        mock_writer.close = MagicMock()
        mock_writer.wait_closed = AsyncMock()

        response = {"success": True}
        mock_reader.read = AsyncMock(side_effect=[
            json.dumps(response).encode(),
            b''
        ])

        with patch('asyncio.open_unix_connection', return_value=(mock_reader, mock_writer)):
            await client._send_request("status_check")

        request = json.loads(written_data[0].decode())
        assert request["method"] == "status_check"
        assert request["params"] == {}

    @pytest.mark.asyncio
    async def test_response_parsing(self, client):
        """Test response is parsed correctly from JSON."""
        mock_reader = AsyncMock()
        mock_writer = AsyncMock()
        mock_writer.write = MagicMock()
        mock_writer.drain = AsyncMock()
        mock_writer.close = MagicMock()
        mock_writer.wait_closed = AsyncMock()

        expected_response = {
            "success": True,
            "data": {"entities": [{"id": 1, "name": "test"}]},
            "count": 1
        }
        mock_reader.read = AsyncMock(side_effect=[
            json.dumps(expected_response).encode(),
            b''
        ])

        with patch('asyncio.open_unix_connection', return_value=(mock_reader, mock_writer)):
            result = await client._send_request("get_data")

        assert result == expected_response
        assert result["success"] is True
        assert result["count"] == 1

    @pytest.mark.asyncio
    async def test_chunked_response_handling(self, client):
        """Test handling of large responses in chunks."""
        mock_reader = AsyncMock()
        mock_writer = AsyncMock()
        mock_writer.write = MagicMock()
        mock_writer.drain = AsyncMock()
        mock_writer.close = MagicMock()
        mock_writer.wait_closed = AsyncMock()

        # Simulate chunked response
        large_response = {"data": "x" * 10000, "success": True}
        response_bytes = json.dumps(large_response).encode()

        # Split into chunks
        chunk_size = 1000
        chunks = [response_bytes[i:i+chunk_size] for i in range(0, len(response_bytes), chunk_size)]
        chunks.append(b'')  # EOF

        mock_reader.read = AsyncMock(side_effect=chunks)

        with patch('asyncio.open_unix_connection', return_value=(mock_reader, mock_writer)):
            result = await client._send_request("get_large_data")

        assert result["success"] is True
        assert len(result["data"]) == 10000


# ============================================================================
# Async Method Tests
# ============================================================================

class TestAsyncMethods:
    """Tests for async client methods."""

    @pytest.fixture
    def client(self):
        return MemoryClient()

    def _setup_mock_connection(self, response_data):
        """Helper to set up mocked connection."""
        mock_reader = AsyncMock()
        mock_writer = AsyncMock()
        mock_writer.write = MagicMock()
        mock_writer.drain = AsyncMock()
        mock_writer.close = MagicMock()
        mock_writer.wait_closed = AsyncMock()
        mock_reader.read = AsyncMock(side_effect=[
            json.dumps(response_data).encode(),
            b''
        ])
        return mock_reader, mock_writer

    @pytest.mark.asyncio
    async def test_create_entities_async(self, client):
        """Test async create_entities method."""
        mock_reader, mock_writer = self._setup_mock_connection({
            "success": True,
            "created": 2
        })

        written_data = []
        mock_writer.write = lambda d: written_data.append(d)

        with patch('asyncio.open_unix_connection', return_value=(mock_reader, mock_writer)):
            result = await client.create_entities([
                {"name": "entity1", "entityType": "test"},
                {"name": "entity2", "entityType": "test"}
            ])

        assert result["success"] is True
        assert result["created"] == 2

        # Verify method and params
        request = json.loads(written_data[0].decode())
        assert request["method"] == "create_entities"
        assert len(request["params"]["entities"]) == 2

    @pytest.mark.asyncio
    async def test_search_nodes_async(self, client):
        """Test async search_nodes method."""
        mock_reader, mock_writer = self._setup_mock_connection({
            "success": True,
            "results": [{"id": 1, "name": "result1"}],
            "count": 1
        })

        written_data = []
        mock_writer.write = lambda d: written_data.append(d)

        with patch('asyncio.open_unix_connection', return_value=(mock_reader, mock_writer)):
            result = await client.search_nodes("test query", limit=5)

        assert result["success"] is True
        assert result["count"] == 1

        request = json.loads(written_data[0].decode())
        assert request["method"] == "search_nodes"
        assert request["params"]["query"] == "test query"
        assert request["params"]["limit"] == 5

    @pytest.mark.asyncio
    async def test_search_nodes_default_limit(self, client):
        """Test search_nodes uses default limit of 10."""
        mock_reader, mock_writer = self._setup_mock_connection({"success": True})

        written_data = []
        mock_writer.write = lambda d: written_data.append(d)

        with patch('asyncio.open_unix_connection', return_value=(mock_reader, mock_writer)):
            await client.search_nodes("query")

        request = json.loads(written_data[0].decode())
        assert request["params"]["limit"] == 10

    @pytest.mark.asyncio
    async def test_get_memory_status_async(self, client):
        """Test async get_memory_status method."""
        mock_reader, mock_writer = self._setup_mock_connection({
            "success": True,
            "entity_count": 100,
            "compression_ratio": 0.8
        })

        with patch('asyncio.open_unix_connection', return_value=(mock_reader, mock_writer)):
            result = await client.get_memory_status()

        assert result["success"] is True
        assert result["entity_count"] == 100

    @pytest.mark.asyncio
    async def test_ping_async(self, client):
        """Test async ping method."""
        mock_reader, mock_writer = self._setup_mock_connection({
            "success": True,
            "pong": True
        })

        with patch('asyncio.open_unix_connection', return_value=(mock_reader, mock_writer)):
            result = await client.ping()

        assert result["success"] is True
        assert result["pong"] is True


# ============================================================================
# Sync Method Tests
# ============================================================================

class TestSyncMethods:
    """Tests for synchronous client methods."""

    @pytest.fixture
    def client(self):
        return MemoryClient()

    def test_create_entities_sync(self, client):
        """Test sync create_entities method."""
        mock_response = {"success": True, "created": 1}

        with patch.object(client, '_send_request', new_callable=AsyncMock) as mock_send:
            mock_send.return_value = mock_response

            with patch('asyncio.run') as mock_run:
                mock_run.return_value = mock_response
                result = client.create_entities_sync([{"name": "test"}])

        assert result == mock_response

    def test_search_nodes_sync(self, client):
        """Test sync search_nodes method."""
        mock_response = {"success": True, "results": []}

        with patch.object(client, '_send_request_sync') as mock_send:
            mock_send.return_value = mock_response
            result = client.search_nodes_sync("query", limit=20)

        mock_send.assert_called_once_with("search_nodes", {"query": "query", "limit": 20})

    def test_get_memory_status_sync(self, client):
        """Test sync get_memory_status method."""
        mock_response = {"success": True, "status": "healthy"}

        with patch.object(client, '_send_request_sync') as mock_send:
            mock_send.return_value = mock_response
            result = client.get_memory_status_sync()

        mock_send.assert_called_once_with("get_memory_status")

    def test_ping_sync(self, client):
        """Test sync ping method."""
        mock_response = {"pong": True}

        with patch.object(client, '_send_request_sync') as mock_send:
            mock_send.return_value = mock_response
            result = client.ping_sync()

        mock_send.assert_called_once_with("ping")


# ============================================================================
# Global Client Singleton Tests
# ============================================================================

class TestGlobalClient:
    """Tests for global client singleton."""

    def setup_method(self):
        """Reset global client before each test."""
        memory_client_module._client = None

    def test_get_client_creates_singleton(self):
        """Test get_client creates singleton on first call."""
        client1 = get_client()
        client2 = get_client()

        assert client1 is client2
        assert isinstance(client1, MemoryClient)

    def test_get_client_default_path(self):
        """Test singleton has default socket path."""
        client = get_client()
        assert client.socket_path == "/tmp/memory-db.sock"

    def test_global_client_reuse(self):
        """Test global client is reused across calls."""
        memory_client_module._client = None

        client1 = get_client()
        client2 = get_client()
        client3 = get_client()

        assert client1 is client2 is client3


# ============================================================================
# Convenience Wrapper Tests
# ============================================================================

class TestConvenienceWrappers:
    """Tests for module-level convenience functions."""

    def setup_method(self):
        """Reset global client before each test."""
        memory_client_module._client = None

    def test_create_entities_wrapper(self):
        """Test create_entities module function."""
        mock_response = {"success": True, "created": 1}

        with patch.object(MemoryClient, 'create_entities_sync', return_value=mock_response) as mock_method:
            result = create_entities([{"name": "test"}])

        assert result == mock_response
        mock_method.assert_called_once_with([{"name": "test"}])

    def test_search_nodes_wrapper(self):
        """Test search_nodes module function."""
        mock_response = {"success": True, "results": []}

        with patch.object(MemoryClient, 'search_nodes_sync', return_value=mock_response) as mock_method:
            result = search_nodes("query", limit=5)

        assert result == mock_response
        mock_method.assert_called_once_with("query", 5)

    def test_search_nodes_wrapper_default_limit(self):
        """Test search_nodes wrapper uses default limit."""
        with patch.object(MemoryClient, 'search_nodes_sync', return_value={}) as mock_method:
            search_nodes("query")

        mock_method.assert_called_once_with("query", 10)

    def test_get_memory_status_wrapper(self):
        """Test get_memory_status module function."""
        mock_response = {"success": True, "entity_count": 50}

        with patch.object(MemoryClient, 'get_memory_status_sync', return_value=mock_response) as mock_method:
            result = get_memory_status()

        assert result == mock_response
        mock_method.assert_called_once()


# ============================================================================
# Error Handling Tests
# ============================================================================

class TestErrorHandling:
    """Tests for error handling scenarios."""

    @pytest.fixture
    def client(self):
        return MemoryClient()

    @pytest.mark.asyncio
    async def test_connection_error_propagates(self, client):
        """Test connection errors propagate correctly."""
        with patch('asyncio.open_unix_connection', side_effect=ConnectionRefusedError("No server")):
            with pytest.raises(ConnectionRefusedError):
                await client._send_request("test")

    @pytest.mark.asyncio
    async def test_json_decode_error(self, client):
        """Test handling of invalid JSON response."""
        mock_reader = AsyncMock()
        mock_writer = AsyncMock()
        mock_writer.write = MagicMock()
        mock_writer.drain = AsyncMock()
        mock_writer.close = MagicMock()
        mock_writer.wait_closed = AsyncMock()

        # Return invalid JSON
        mock_reader.read = AsyncMock(side_effect=[b'not valid json{', b''])

        with patch('asyncio.open_unix_connection', return_value=(mock_reader, mock_writer)):
            with pytest.raises(json.JSONDecodeError):
                await client._send_request("test")

    @pytest.mark.asyncio
    async def test_writer_cleanup_on_error(self, client):
        """Test writer is closed even on error."""
        mock_reader = AsyncMock()
        mock_writer = AsyncMock()
        mock_writer.write = MagicMock()
        mock_writer.drain = AsyncMock()
        mock_writer.close = MagicMock()
        mock_writer.wait_closed = AsyncMock()

        # Cause error during read
        mock_reader.read = AsyncMock(side_effect=Exception("Read error"))

        with patch('asyncio.open_unix_connection', return_value=(mock_reader, mock_writer)):
            with pytest.raises(Exception, match="Read error"):
                await client._send_request("test")

        # Verify cleanup was attempted
        mock_writer.close.assert_called_once()
        mock_writer.wait_closed.assert_called_once()


# ============================================================================
# Edge Case Tests
# ============================================================================

class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    @pytest.fixture
    def client(self):
        return MemoryClient()

    @pytest.mark.asyncio
    async def test_empty_response(self, client):
        """Test handling of empty response body."""
        mock_reader = AsyncMock()
        mock_writer = AsyncMock()
        mock_writer.write = MagicMock()
        mock_writer.drain = AsyncMock()
        mock_writer.close = MagicMock()
        mock_writer.wait_closed = AsyncMock()

        # Empty response then EOF
        mock_reader.read = AsyncMock(side_effect=[b'{}', b''])

        with patch('asyncio.open_unix_connection', return_value=(mock_reader, mock_writer)):
            result = await client._send_request("test")

        assert result == {}

    @pytest.mark.asyncio
    async def test_immediate_eof(self, client):
        """Test handling of immediate EOF (empty bytes response)."""
        mock_reader = AsyncMock()
        mock_writer = AsyncMock()
        mock_writer.write = MagicMock()
        mock_writer.drain = AsyncMock()
        mock_writer.close = MagicMock()
        mock_writer.wait_closed = AsyncMock()

        # Immediate EOF
        mock_reader.read = AsyncMock(return_value=b'')

        with patch('asyncio.open_unix_connection', return_value=(mock_reader, mock_writer)):
            with pytest.raises(json.JSONDecodeError):
                await client._send_request("test")

    @pytest.mark.asyncio
    async def test_unicode_in_request_params(self, client):
        """Test handling of unicode in request parameters."""
        mock_reader = AsyncMock()
        mock_writer = AsyncMock()

        written_data = []
        mock_writer.write = lambda d: written_data.append(d)
        mock_writer.drain = AsyncMock()
        mock_writer.close = MagicMock()
        mock_writer.wait_closed = AsyncMock()

        mock_reader.read = AsyncMock(side_effect=[b'{"success": true}', b''])

        with patch('asyncio.open_unix_connection', return_value=(mock_reader, mock_writer)):
            await client._send_request("search", {"query": "日本語テスト"})

        # Verify unicode was encoded correctly
        request = json.loads(written_data[0].decode())
        assert request["params"]["query"] == "日本語テスト"

    @pytest.mark.asyncio
    async def test_unicode_in_response(self, client):
        """Test handling of unicode in response."""
        mock_reader = AsyncMock()
        mock_writer = AsyncMock()
        mock_writer.write = MagicMock()
        mock_writer.drain = AsyncMock()
        mock_writer.close = MagicMock()
        mock_writer.wait_closed = AsyncMock()

        response = {"result": "日本語レスポンス", "emoji": "🎉"}
        mock_reader.read = AsyncMock(side_effect=[
            json.dumps(response).encode('utf-8'),
            b''
        ])

        with patch('asyncio.open_unix_connection', return_value=(mock_reader, mock_writer)):
            result = await client._send_request("test")

        assert result["result"] == "日本語レスポンス"
        assert result["emoji"] == "🎉"

    @pytest.mark.asyncio
    async def test_null_params_handling(self, client):
        """Test None params is converted to empty dict."""
        mock_reader = AsyncMock()
        mock_writer = AsyncMock()

        written_data = []
        mock_writer.write = lambda d: written_data.append(d)
        mock_writer.drain = AsyncMock()
        mock_writer.close = MagicMock()
        mock_writer.wait_closed = AsyncMock()

        mock_reader.read = AsyncMock(side_effect=[b'{}', b''])

        with patch('asyncio.open_unix_connection', return_value=(mock_reader, mock_writer)):
            await client._send_request("test", None)

        request = json.loads(written_data[0].decode())
        assert request["params"] == {}

    def test_multiple_clients_different_paths(self):
        """Test multiple clients can have different socket paths."""
        client1 = MemoryClient("/path/one.sock")
        client2 = MemoryClient("/path/two.sock")

        assert client1.socket_path != client2.socket_path
        assert client1.socket_path == "/path/one.sock"
        assert client2.socket_path == "/path/two.sock"


# ============================================================================
# Integration-Style Tests (with mocking)
# ============================================================================

class TestIntegrationPatterns:
    """Tests simulating real usage patterns."""

    def setup_method(self):
        """Reset global client."""
        memory_client_module._client = None

    def test_typical_entity_workflow(self):
        """Test typical create -> search -> status workflow."""
        # Mock all the sync methods
        with patch.object(MemoryClient, 'create_entities_sync') as mock_create, \
             patch.object(MemoryClient, 'search_nodes_sync') as mock_search, \
             patch.object(MemoryClient, 'get_memory_status_sync') as mock_status:

            mock_create.return_value = {"success": True, "created": 1, "entity_id": 123}
            mock_search.return_value = {"success": True, "results": [{"id": 123, "name": "test"}]}
            mock_status.return_value = {"success": True, "entity_count": 1}

            # Simulate workflow
            create_result = create_entities([{
                "name": "test_entity",
                "entityType": "knowledge",
                "observations": ["test observation"]
            }])

            search_result = search_nodes("test_entity")

            status_result = get_memory_status()

            # Verify workflow
            assert create_result["success"] is True
            assert create_result["entity_id"] == 123
            assert len(search_result["results"]) == 1
            assert status_result["entity_count"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
