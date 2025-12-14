"""Tests for network_scanner_mcp.utils module."""

import json
import os
import tempfile
from pathlib import Path
from datetime import datetime, timedelta

import pytest

from network_scanner_mcp.utils import (
    normalize_mac,
    get_timestamp,
    parse_timestamp,
    is_recent,
    load_json_file,
    save_json_file,
    load_cluster_nodes,
    _normalize_cluster_config,
    get_cluster_node_display_name,
    get_config_value,
)


class TestNormalizeMac:
    """Tests for normalize_mac function."""

    def test_uppercase_conversion(self):
        """Test that MAC addresses are converted to uppercase."""
        assert normalize_mac("aa:bb:cc:dd:ee:ff") == "AA:BB:CC:DD:EE:FF"

    def test_already_uppercase(self):
        """Test MAC addresses already in uppercase."""
        assert normalize_mac("AA:BB:CC:DD:EE:FF") == "AA:BB:CC:DD:EE:FF"

    def test_mixed_case(self):
        """Test mixed case MAC addresses."""
        assert normalize_mac("Aa:Bb:Cc:Dd:Ee:Ff") == "AA:BB:CC:DD:EE:FF"

    def test_dash_separator(self):
        """Test MAC addresses with dash separators."""
        assert normalize_mac("aa-bb-cc-dd-ee-ff") == "AA:BB:CC:DD:EE:FF"

    def test_no_separator(self):
        """Test MAC addresses without separators."""
        assert normalize_mac("aabbccddeeff") == "AA:BB:CC:DD:EE:FF"

    def test_invalid_length(self):
        """Test handling of invalid MAC addresses."""
        # Should return uppercase version even if invalid length
        result = normalize_mac("aabbcc")
        assert result == "AABBCC"


class TestTimestamps:
    """Tests for timestamp functions."""

    def test_get_timestamp_format(self):
        """Test that timestamp is in ISO format."""
        ts = get_timestamp()
        # Should be parseable
        parsed = datetime.fromisoformat(ts)
        assert isinstance(parsed, datetime)

    def test_parse_timestamp_valid(self):
        """Test parsing valid timestamp."""
        ts = "2024-01-15T12:30:45"
        result = parse_timestamp(ts)
        assert result is not None
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15

    def test_parse_timestamp_invalid(self):
        """Test parsing invalid timestamp."""
        assert parse_timestamp("not a timestamp") is None
        assert parse_timestamp("") is None
        assert parse_timestamp(None) is None

    def test_is_recent_true(self):
        """Test is_recent returns True for recent timestamps."""
        ts = get_timestamp()
        assert is_recent(ts, max_age_seconds=60) is True

    def test_is_recent_false(self):
        """Test is_recent returns False for old timestamps."""
        old = (datetime.now() - timedelta(hours=1)).isoformat()
        assert is_recent(old, max_age_seconds=60) is False

    def test_is_recent_invalid(self):
        """Test is_recent with invalid timestamp."""
        assert is_recent("invalid", max_age_seconds=60) is False


class TestJsonOperations:
    """Tests for JSON file operations."""

    def test_load_json_file_exists(self, tmp_path):
        """Test loading existing JSON file."""
        test_data = {"key": "value", "number": 42}
        file_path = tmp_path / "test.json"
        file_path.write_text(json.dumps(test_data))

        result = load_json_file(file_path)
        assert result == test_data

    def test_load_json_file_not_exists(self, tmp_path):
        """Test loading non-existent file returns default."""
        file_path = tmp_path / "nonexistent.json"
        result = load_json_file(file_path)
        assert result == {}

    def test_load_json_file_custom_default(self, tmp_path):
        """Test loading non-existent file with custom default."""
        file_path = tmp_path / "nonexistent.json"
        default = {"default": True}
        result = load_json_file(file_path, default)
        assert result == default

    def test_load_json_file_invalid(self, tmp_path):
        """Test loading invalid JSON returns default."""
        file_path = tmp_path / "invalid.json"
        file_path.write_text("not valid json {")
        result = load_json_file(file_path)
        assert result == {}

    def test_load_json_file_empty(self, tmp_path):
        """Test loading empty file returns default."""
        file_path = tmp_path / "empty.json"
        file_path.write_text("")
        result = load_json_file(file_path)
        assert result == {}

    def test_save_json_file(self, tmp_path):
        """Test saving JSON file."""
        test_data = {"key": "value", "list": [1, 2, 3]}
        file_path = tmp_path / "output.json"

        result = save_json_file(file_path, test_data)
        assert result is True
        assert file_path.exists()

        loaded = json.loads(file_path.read_text())
        assert loaded == test_data

    def test_save_json_file_creates_dirs(self, tmp_path):
        """Test that save_json_file creates parent directories."""
        file_path = tmp_path / "subdir" / "deep" / "output.json"

        result = save_json_file(file_path, {"test": True})
        assert result is True
        assert file_path.exists()


class TestClusterNodeConfig:
    """Tests for cluster node configuration functions."""

    def test_normalize_simple_format(self):
        """Test normalizing simple string format."""
        raw = {
            "192.168.1.1": "node-1 (orchestrator)",
            "192.168.1.2": "node-2 (worker)"
        }

        result = _normalize_cluster_config(raw)

        assert "192.168.1.1" in result
        assert result["192.168.1.1"]["name"] == "node-1"
        assert result["192.168.1.1"]["role"] == "orchestrator"

    def test_normalize_full_format(self):
        """Test normalizing full dict format."""
        raw = {
            "192.168.1.1": {
                "name": "node-1",
                "role": "orchestrator",
                "type": "cluster_node"
            }
        }

        result = _normalize_cluster_config(raw)

        assert result["192.168.1.1"]["name"] == "node-1"
        assert result["192.168.1.1"]["role"] == "orchestrator"

    def test_normalize_simple_name_only(self):
        """Test normalizing name without role in parentheses."""
        raw = {"192.168.1.1": "simple-node"}

        result = _normalize_cluster_config(raw)

        assert result["192.168.1.1"]["name"] == "simple-node"
        assert result["192.168.1.1"]["role"] == "node"

    def test_get_cluster_node_display_name(self):
        """Test getting display name for cluster node."""
        nodes = {
            "192.168.1.1": {"name": "node-1", "role": "orchestrator", "type": "cluster_node"}
        }

        result = get_cluster_node_display_name("192.168.1.1", nodes)
        assert result == "node-1 (orchestrator)"

    def test_get_cluster_node_display_name_unknown(self):
        """Test getting display name for unknown node."""
        nodes = {}
        result = get_cluster_node_display_name("192.168.1.99", nodes)
        assert result == "192.168.1.99"

    def test_load_cluster_nodes_from_env(self, monkeypatch, tmp_path):
        """Test loading cluster nodes from environment variable."""
        config = {"192.168.1.1": {"name": "test", "role": "worker", "type": "cluster_node"}}
        monkeypatch.setenv("CLUSTER_NODES_JSON", json.dumps(config))

        result = load_cluster_nodes(tmp_path / "nonexistent.json")

        assert "192.168.1.1" in result
        assert result["192.168.1.1"]["name"] == "test"

    def test_load_cluster_nodes_from_file(self, tmp_path):
        """Test loading cluster nodes from file."""
        config = {"192.168.1.1": {"name": "file-node", "role": "builder", "type": "cluster_node"}}
        config_file = tmp_path / "cluster_nodes.json"
        config_file.write_text(json.dumps(config))

        result = load_cluster_nodes(config_file)

        assert "192.168.1.1" in result
        assert result["192.168.1.1"]["name"] == "file-node"


class TestGetConfigValue:
    """Tests for get_config_value function."""

    def test_string_value(self, monkeypatch):
        """Test getting string configuration value."""
        monkeypatch.setenv("TEST_STRING", "hello")
        result = get_config_value("TEST_STRING", "default", str)
        assert result == "hello"

    def test_int_value(self, monkeypatch):
        """Test getting integer configuration value."""
        monkeypatch.setenv("TEST_INT", "42")
        result = get_config_value("TEST_INT", 0, int)
        assert result == 42

    def test_bool_value_true(self, monkeypatch):
        """Test getting boolean true configuration value."""
        for val in ["true", "True", "TRUE", "1", "yes", "on"]:
            monkeypatch.setenv("TEST_BOOL", val)
            result = get_config_value("TEST_BOOL", False, bool)
            assert result is True, f"Failed for value: {val}"

    def test_bool_value_false(self, monkeypatch):
        """Test getting boolean false configuration value."""
        for val in ["false", "False", "FALSE", "0", "no", "off"]:
            monkeypatch.setenv("TEST_BOOL", val)
            result = get_config_value("TEST_BOOL", True, bool)
            assert result is False, f"Failed for value: {val}"

    def test_default_value(self, monkeypatch):
        """Test default value when env var not set."""
        monkeypatch.delenv("NONEXISTENT_VAR", raising=False)
        result = get_config_value("NONEXISTENT_VAR", "default", str)
        assert result == "default"

    def test_invalid_cast(self, monkeypatch):
        """Test handling of invalid type cast."""
        monkeypatch.setenv("TEST_INVALID", "not_a_number")
        result = get_config_value("TEST_INVALID", 99, int)
        assert result == 99  # Should return default on cast failure
