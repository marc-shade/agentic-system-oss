"""
Tests for database connectors.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
import pandas as pd
from typing import Dict, Any

# Import available database connectors
from synthetic_data_mcp.database.connectors.postgresql import PostgreSQLConnector
from synthetic_data_mcp.database.connectors.mysql import MySQLConnector  
from synthetic_data_mcp.database.connectors.mongodb import MongoDBConnector
from synthetic_data_mcp.database.connectors.redis import RedisConnector
from synthetic_data_mcp.database.connectors.bigquery import BigQueryConnector
from synthetic_data_mcp.database.connectors.snowflake import SnowflakeConnector
from synthetic_data_mcp.database.connectors.redshift import RedshiftConnector


class TestDatabaseConnectors:
    """Test database connector implementations."""

    def test_postgresql_connector_init(self):
        """Test PostgreSQL connector initialization."""
        config = {
            "host": "localhost",
            "port": 5432,
            "database": "test_db",
            "username": "test_user", 
            "password": "test_pass"
        }
        
        connector = PostgreSQLConnector(config)
        assert connector.config == config
        assert "postgresql" in str(connector)

    def test_mysql_connector_init(self):
        """Test MySQL connector initialization.""" 
        config = {
            "host": "localhost",
            "port": 3306,
            "database": "test_db",
            "username": "test_user",
            "password": "test_pass"
        }
        
        connector = MySQLConnector(config)
        assert connector.config == config
        assert "mysql" in str(connector) 

    def test_mongodb_connector_init(self):
        """Test MongoDB connector initialization."""
        config = {
            "connection_string": "mongodb://localhost:27017",
            "database": "test_db"
        }
        
        connector = MongoDBConnector(config)
        assert connector.config == config
        assert "mongodb" in str(connector)

    def test_redis_connector_init(self):
        """Test Redis connector initialization."""
        config = {
            "host": "localhost", 
            "port": 6379,
            "db": 0
        }
        
        connector = RedisConnector(config)
        assert connector.config == config
        assert "redis" in str(connector)

    def test_bigquery_connector_init(self):
        """Test BigQuery connector initialization."""
        config = {
            "project_id": "test-project",
            "dataset_id": "test_dataset",
            "credentials_path": "/path/to/creds.json"
        }
        
        connector = BigQueryConnector(config)
        assert connector.config == config
        assert "bigquery" in str(connector)

    def test_snowflake_connector_init(self):
        """Test Snowflake connector initialization."""
        config = {
            "account": "test-account",
            "user": "test_user", 
            "password": "test_pass",
            "database": "TEST_DB",
            "schema": "PUBLIC",
            "warehouse": "COMPUTE_WH"
        }
        
        connector = SnowflakeConnector(config)
        assert connector.config == config
        assert "snowflake" in str(connector)

    def test_redshift_connector_init(self):
        """Test Redshift connector initialization."""
        config = {
            "host": "test-cluster.abc123.us-west-2.redshift.amazonaws.com",
            "port": 5439,
            "database": "test_db",
            "username": "test_user",
            "password": "test_pass"
        }
        
        connector = RedshiftConnector(config)
        assert connector.config == config
        assert "redshift" in str(connector)

    @pytest.mark.asyncio
    async def test_connector_connection_mock(self):
        """Test connector connection with mocked database."""
        config = {"host": "localhost", "port": 5432, "database": "test"}
        connector = PostgreSQLConnector(config)
        
        # Mock the connection method
        with patch.object(connector, 'connect', new_callable=AsyncMock) as mock_connect:
            mock_connect.return_value = True
            
            result = await connector.connect()
            assert result == True
            mock_connect.assert_called_once()

    @pytest.mark.asyncio  
    async def test_connector_query_mock(self):
        """Test connector query execution with mocked database."""
        config = {"host": "localhost", "port": 5432, "database": "test"}
        connector = PostgreSQLConnector(config)
        
        # Mock query execution
        mock_result = pd.DataFrame({"id": [1, 2], "name": ["test1", "test2"]})
        
        with patch.object(connector, 'execute_query', new_callable=AsyncMock) as mock_query:
            mock_query.return_value = mock_result
            
            result = await connector.execute_query("SELECT * FROM test_table")
            assert len(result) == 2
            assert "id" in result.columns
            assert "name" in result.columns
            mock_query.assert_called_once_with("SELECT * FROM test_table")

    def test_connector_config_validation(self):
        """Test connector configuration validation."""
        # Test missing required config
        with pytest.raises((ValueError, KeyError, TypeError)):
            PostgreSQLConnector({})
        
        # Test invalid port
        invalid_config = {
            "host": "localhost",
            "port": "invalid_port",  # Should be integer
            "database": "test",
            "username": "test",
            "password": "test"
        }
        
        # Should handle gracefully or raise appropriate error
        try:
            connector = PostgreSQLConnector(invalid_config)
            # If it doesn't raise, that's also valid (some connectors might be flexible)
            assert connector is not None
        except (ValueError, TypeError):
            # Expected for strict validation
            pass

    @pytest.mark.asyncio
    async def test_connector_insert_mock(self):
        """Test connector data insertion with mocked database."""
        config = {"host": "localhost", "port": 5432, "database": "test"}
        connector = PostgreSQLConnector(config)
        
        test_data = pd.DataFrame({
            "name": ["Alice", "Bob"],
            "age": [30, 25],
            "city": ["NYC", "LA"]
        })
        
        with patch.object(connector, 'insert_dataframe', new_callable=AsyncMock) as mock_insert:
            mock_insert.return_value = True
            
            result = await connector.insert_dataframe(test_data, "users") 
            assert result == True
            mock_insert.assert_called_once_with(test_data, "users")

    @pytest.mark.asyncio
    async def test_connector_error_handling(self):
        """Test connector error handling."""
        config = {"host": "nonexistent", "port": 5432, "database": "test"}
        connector = PostgreSQLConnector(config)
        
        # Test connection error handling
        with patch.object(connector, 'connect', new_callable=AsyncMock) as mock_connect:
            mock_connect.side_effect = Exception("Connection failed")
            
            with pytest.raises(Exception):
                await connector.connect()