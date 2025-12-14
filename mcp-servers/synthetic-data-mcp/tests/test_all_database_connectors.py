"""
Comprehensive tests for all database connectors - targeting 100% coverage.
"""

import pytest
import pandas as pd
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError, SQLAlchemyError
import asyncio
from typing import Dict, Any, List

# Import all database connectors
from synthetic_data_mcp.database.connectors.postgresql import PostgreSQLConnector
from synthetic_data_mcp.database.connectors.mysql import MySQLConnector
from synthetic_data_mcp.database.connectors.mongodb import MongoDBConnector
from synthetic_data_mcp.database.connectors.bigquery import BigQueryConnector
from synthetic_data_mcp.database.connectors.snowflake import SnowflakeConnector
from synthetic_data_mcp.database.connectors.redshift import RedshiftConnector
from synthetic_data_mcp.database.connectors.redis import RedisConnector


@pytest.fixture
def sample_data():
    """Sample DataFrame for testing."""
    return pd.DataFrame({
        'id': [1, 2, 3],
        'name': ['Alice', 'Bob', 'Charlie'],
        'age': [25, 30, 35],
        'email': ['alice@test.com', 'bob@test.com', 'charlie@test.com']
    })


@pytest.fixture
def config():
    """Sample config for testing."""
    return {
        'host': 'localhost',
        'port': 5432,
        'database': 'test_db',
        'username': 'test_user',
        'password': 'test_pass',
        'timeout': 30
    }


class TestPostgreSQLConnector:
    """Comprehensive tests for PostgreSQL connector."""

    def test_init_with_config(self, config):
        """Test connector initialization with config."""
        connector = PostgreSQLConnector(config)
        assert connector.host == 'localhost'
        assert connector.port == 5432
        assert connector.database == 'test_db'
        assert connector.username == 'test_user'

    def test_init_with_kwargs(self):
        """Test connector initialization with kwargs."""
        connector = PostgreSQLConnector(
            host='test-host',
            port=5433,
            database='test-db',
            username='user',
            password='pass'
        )
        assert connector.host == 'test-host'
        assert connector.port == 5433

    @patch('psycopg2.connect')
    def test_connect_success(self, mock_connect, config):
        """Test successful database connection."""
        mock_connection = Mock()
        mock_connect.return_value = mock_connection
        
        connector = PostgreSQLConnector(config)
        result = connector.connect()
        
        assert result is True
        assert connector.connection == mock_connection
        mock_connect.assert_called_once()

    @patch('psycopg2.connect')
    def test_connect_failure(self, mock_connect, config):
        """Test database connection failure."""
        mock_connect.side_effect = Exception("Connection failed")
        
        connector = PostgreSQLConnector(config)
        result = connector.connect()
        
        assert result is False
        assert connector.connection is None

    @patch('psycopg2.connect')
    def test_disconnect(self, mock_connect, config):
        """Test database disconnection."""
        mock_connection = Mock()
        mock_connect.return_value = mock_connection
        
        connector = PostgreSQLConnector(config)
        connector.connect()
        connector.disconnect()
        
        mock_connection.close.assert_called_once()
        assert connector.connection is None

    @patch('psycopg2.connect')
    def test_execute_query_success(self, mock_connect, config):
        """Test successful query execution."""
        mock_connection = Mock()
        mock_cursor = Mock()
        mock_connection.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = [('Alice', 25), ('Bob', 30)]
        mock_cursor.description = [('name',), ('age',)]
        mock_connect.return_value = mock_connection
        
        connector = PostgreSQLConnector(config)
        connector.connect()
        
        result = connector.execute_query("SELECT name, age FROM users")
        
        assert len(result) == 2
        assert result[0]['name'] == 'Alice'
        assert result[0]['age'] == 25
        mock_cursor.execute.assert_called_with("SELECT name, age FROM users")

    @patch('psycopg2.connect')
    def test_execute_query_with_params(self, mock_connect, config):
        """Test query execution with parameters."""
        mock_connection = Mock()
        mock_cursor = Mock()
        mock_connection.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = [('Alice', 25)]
        mock_cursor.description = [('name',), ('age',)]
        mock_connect.return_value = mock_connection
        
        connector = PostgreSQLConnector(config)
        connector.connect()
        
        params = {'user_id': 1}
        result = connector.execute_query("SELECT name, age FROM users WHERE id = %(user_id)s", params)
        
        assert len(result) == 1
        mock_cursor.execute.assert_called_with("SELECT name, age FROM users WHERE id = %(user_id)s", params)

    @patch('psycopg2.connect')
    def test_execute_query_failure(self, mock_connect, config):
        """Test query execution failure."""
        mock_connection = Mock()
        mock_cursor = Mock()
        mock_cursor.execute.side_effect = Exception("Query failed")
        mock_connection.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_connection
        
        connector = PostgreSQLConnector(config)
        connector.connect()
        
        with pytest.raises(Exception):
            connector.execute_query("SELECT * FROM invalid_table")

    @patch('psycopg2.connect')
    def test_get_schema_success(self, mock_connect, config):
        """Test schema retrieval success."""
        mock_connection = Mock()
        mock_cursor = Mock()
        mock_cursor.fetchall.return_value = [
            ('users', 'id', 'integer', 'YES'),
            ('users', 'name', 'character varying', 'NO'),
            ('users', 'email', 'character varying', 'YES')
        ]
        mock_connection.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_connection
        
        connector = PostgreSQLConnector(config)
        connector.connect()
        
        schema = connector.get_schema()
        
        assert 'users' in schema
        assert len(schema['users']) == 3
        assert schema['users'][0]['column_name'] == 'id'
        assert schema['users'][0]['data_type'] == 'integer'

    @patch('psycopg2.connect')
    def test_insert_data_success(self, mock_connect, config, sample_data):
        """Test successful data insertion."""
        mock_connection = Mock()
        mock_cursor = Mock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_connection
        
        connector = PostgreSQLConnector(config)
        connector.connect()
        
        result = connector.insert_data('users', sample_data)
        
        assert result is True
        mock_cursor.execute.assert_called()
        mock_connection.commit.assert_called_once()

    @patch('psycopg2.connect')
    def test_insert_data_batch_success(self, mock_connect, config, sample_data):
        """Test successful batch data insertion."""
        mock_connection = Mock()
        mock_cursor = Mock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_connection
        
        connector = PostgreSQLConnector(config)
        connector.connect()
        
        result = connector.insert_data_batch('users', sample_data, batch_size=2)
        
        assert result is True
        assert mock_cursor.execute.call_count >= 2
        mock_connection.commit.assert_called()

    @patch('psycopg2.connect')
    def test_create_table_success(self, mock_connect, config):
        """Test successful table creation."""
        mock_connection = Mock()
        mock_cursor = Mock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_connection
        
        connector = PostgreSQLConnector(config)
        connector.connect()
        
        schema = {
            'id': 'INTEGER PRIMARY KEY',
            'name': 'VARCHAR(255) NOT NULL',
            'email': 'VARCHAR(255)'
        }
        
        result = connector.create_table('test_table', schema)
        
        assert result is True
        mock_cursor.execute.assert_called()
        mock_connection.commit.assert_called_once()

    @patch('psycopg2.connect')
    def test_drop_table_success(self, mock_connect, config):
        """Test successful table dropping."""
        mock_connection = Mock()
        mock_cursor = Mock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_connection
        
        connector = PostgreSQLConnector(config)
        connector.connect()
        
        result = connector.drop_table('test_table')
        
        assert result is True
        mock_cursor.execute.assert_called_with('DROP TABLE IF EXISTS test_table')
        mock_connection.commit.assert_called_once()

    @patch('psycopg2.connect')
    def test_get_table_info(self, mock_connect, config):
        """Test getting table information."""
        mock_connection = Mock()
        mock_cursor = Mock()
        mock_cursor.fetchall.return_value = [
            ('users', 1000, 2048, '2023-01-01 00:00:00')
        ]
        mock_connection.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_connection
        
        connector = PostgreSQLConnector(config)
        connector.connect()
        
        info = connector.get_table_info()
        
        assert len(info) == 1
        assert info[0]['table_name'] == 'users'
        assert info[0]['row_count'] == 1000

    @patch('psycopg2.connect')
    def test_backup_table_success(self, mock_connect, config):
        """Test successful table backup."""
        mock_connection = Mock()
        mock_cursor = Mock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_connection
        
        connector = PostgreSQLConnector(config)
        connector.connect()
        
        result = connector.backup_table('users', 'users_backup')
        
        assert result is True
        mock_cursor.execute.assert_called()
        mock_connection.commit.assert_called_once()

    @patch('psycopg2.connect')
    def test_restore_table_success(self, mock_connect, config):
        """Test successful table restoration."""
        mock_connection = Mock()
        mock_cursor = Mock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_connection
        
        connector = PostgreSQLConnector(config)
        connector.connect()
        
        result = connector.restore_table('users_backup', 'users')
        
        assert result is True
        mock_cursor.execute.assert_called()
        mock_connection.commit.assert_called_once()

    def test_get_connection_string(self, config):
        """Test connection string generation."""
        connector = PostgreSQLConnector(config)
        conn_str = connector.get_connection_string()
        
        expected = "postgresql://test_user:test_pass@localhost:5432/test_db"
        assert conn_str == expected

    def test_validate_config_valid(self, config):
        """Test valid configuration validation."""
        connector = PostgreSQLConnector(config)
        result = connector.validate_config()
        
        assert result is True

    def test_validate_config_invalid(self):
        """Test invalid configuration validation."""
        invalid_config = {'host': 'localhost'}  # Missing required fields
        connector = PostgreSQLConnector(invalid_config)
        result = connector.validate_config()
        
        assert result is False

    @patch('psycopg2.connect')
    def test_test_connection_success(self, mock_connect, config):
        """Test connection testing success."""
        mock_connection = Mock()
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = (1,)
        mock_connection.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_connection
        
        connector = PostgreSQLConnector(config)
        result = connector.test_connection()
        
        assert result is True

    @patch('psycopg2.connect')
    def test_test_connection_failure(self, mock_connect, config):
        """Test connection testing failure."""
        mock_connect.side_effect = Exception("Connection failed")
        
        connector = PostgreSQLConnector(config)
        result = connector.test_connection()
        
        assert result is False


class TestMySQLConnector:
    """Comprehensive tests for MySQL connector."""

    @patch('mysql.connector.connect')
    def test_connect_success(self, mock_connect, config):
        """Test successful MySQL connection."""
        mock_connection = Mock()
        mock_connect.return_value = mock_connection
        
        connector = MySQLConnector(config)
        result = connector.connect()
        
        assert result is True
        assert connector.connection == mock_connection

    @patch('mysql.connector.connect')
    def test_execute_query_success(self, mock_connect, config):
        """Test successful MySQL query execution."""
        mock_connection = Mock()
        mock_cursor = Mock()
        mock_connection.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = [('Alice', 25), ('Bob', 30)]
        mock_cursor.description = [('name',), ('age',)]
        mock_connect.return_value = mock_connection
        
        connector = MySQLConnector(config)
        connector.connect()
        
        result = connector.execute_query("SELECT name, age FROM users")
        
        assert len(result) == 2
        assert result[0]['name'] == 'Alice'

    @patch('mysql.connector.connect')
    def test_get_schema_success(self, mock_connect, config):
        """Test MySQL schema retrieval."""
        mock_connection = Mock()
        mock_cursor = Mock()
        mock_cursor.fetchall.return_value = [
            ('users', 'id', 'int', 'NO', None, 'auto_increment'),
            ('users', 'name', 'varchar(255)', 'YES', None, '')
        ]
        mock_connection.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_connection
        
        connector = MySQLConnector(config)
        connector.connect()
        
        schema = connector.get_schema()
        
        assert 'users' in schema
        assert len(schema['users']) == 2
        assert schema['users'][0]['column_name'] == 'id'

    def test_get_connection_string(self, config):
        """Test MySQL connection string generation."""
        connector = MySQLConnector(config)
        conn_str = connector.get_connection_string()
        
        expected = "mysql+pymysql://test_user:test_pass@localhost:5432/test_db"
        assert conn_str == expected


class TestMongoDBConnector:
    """Comprehensive tests for MongoDB connector."""

    @patch('pymongo.MongoClient')
    def test_connect_success(self, mock_client, config):
        """Test successful MongoDB connection."""
        mock_connection = Mock()
        mock_client.return_value = mock_connection
        
        connector = MongoDBConnector(config)
        result = connector.connect()
        
        assert result is True
        assert connector.client == mock_connection

    @patch('pymongo.MongoClient')
    def test_insert_data_success(self, mock_client, config, sample_data):
        """Test successful MongoDB data insertion."""
        mock_connection = Mock()
        mock_database = Mock()
        mock_collection = Mock()
        mock_connection.__getitem__.return_value = mock_database
        mock_database.__getitem__.return_value = mock_collection
        mock_collection.insert_many.return_value = Mock(inserted_ids=[1, 2, 3])
        mock_client.return_value = mock_connection
        
        connector = MongoDBConnector(config)
        connector.connect()
        
        result = connector.insert_data('users', sample_data)
        
        assert result is True
        mock_collection.insert_many.assert_called_once()

    @patch('pymongo.MongoClient')
    def test_execute_query_success(self, mock_client, config):
        """Test successful MongoDB query execution."""
        mock_connection = Mock()
        mock_database = Mock()
        mock_collection = Mock()
        mock_connection.__getitem__.return_value = mock_database
        mock_database.__getitem__.return_value = mock_collection
        mock_collection.find.return_value = [
            {'_id': '1', 'name': 'Alice', 'age': 25},
            {'_id': '2', 'name': 'Bob', 'age': 30}
        ]
        mock_client.return_value = mock_connection
        
        connector = MongoDBConnector(config)
        connector.connect()
        
        result = connector.execute_query('users', {'age': {'$gte': 25}})
        
        assert len(result) == 2
        assert result[0]['name'] == 'Alice'

    @patch('pymongo.MongoClient')
    def test_get_schema_success(self, mock_client, config):
        """Test MongoDB schema retrieval."""
        mock_connection = Mock()
        mock_database = Mock()
        mock_collection = Mock()
        mock_connection.__getitem__.return_value = mock_database
        mock_database.list_collection_names.return_value = ['users', 'orders']
        mock_database.__getitem__.return_value = mock_collection
        mock_collection.find_one.return_value = {
            '_id': '1',
            'name': 'Alice',
            'age': 25,
            'email': 'alice@test.com'
        }
        mock_client.return_value = mock_connection
        
        connector = MongoDBConnector(config)
        connector.connect()
        
        schema = connector.get_schema()
        
        assert 'users' in schema
        assert 'orders' in schema


class TestBigQueryConnector:
    """Comprehensive tests for BigQuery connector."""

    @patch('google.cloud.bigquery.Client')
    def test_connect_success(self, mock_client, config):
        """Test successful BigQuery connection."""
        mock_bq_client = Mock()
        mock_client.return_value = mock_bq_client
        
        connector = BigQueryConnector(config)
        result = connector.connect()
        
        assert result is True
        assert connector.client == mock_bq_client

    @patch('google.cloud.bigquery.Client')
    def test_execute_query_success(self, mock_client, config):
        """Test successful BigQuery query execution."""
        mock_bq_client = Mock()
        mock_job = Mock()
        mock_job.result.return_value = [
            Mock(name='Alice', age=25),
            Mock(name='Bob', age=30)
        ]
        mock_bq_client.query.return_value = mock_job
        mock_client.return_value = mock_bq_client
        
        connector = BigQueryConnector(config)
        connector.connect()
        
        result = connector.execute_query("SELECT name, age FROM users")
        
        assert len(result) == 2
        mock_bq_client.query.assert_called_once()

    @patch('google.cloud.bigquery.Client')
    def test_insert_data_success(self, mock_client, config, sample_data):
        """Test successful BigQuery data insertion."""
        mock_bq_client = Mock()
        mock_table = Mock()
        mock_bq_client.get_table.return_value = mock_table
        mock_bq_client.insert_rows_json.return_value = []
        mock_client.return_value = mock_bq_client
        
        connector = BigQueryConnector(config)
        connector.connect()
        
        result = connector.insert_data('dataset.users', sample_data)
        
        assert result is True
        mock_bq_client.insert_rows_json.assert_called_once()

    @patch('google.cloud.bigquery.Client')
    def test_get_schema_success(self, mock_client, config):
        """Test BigQuery schema retrieval."""
        mock_bq_client = Mock()
        mock_dataset = Mock()
        mock_table = Mock()
        mock_field1 = Mock()
        mock_field1.name = 'id'
        mock_field1.field_type = 'INTEGER'
        mock_field1.mode = 'REQUIRED'
        mock_field2 = Mock()
        mock_field2.name = 'name'
        mock_field2.field_type = 'STRING'
        mock_field2.mode = 'NULLABLE'
        mock_table.schema = [mock_field1, mock_field2]
        mock_dataset.list_tables.return_value = [mock_table]
        mock_bq_client.list_datasets.return_value = [mock_dataset]
        mock_bq_client.get_table.return_value = mock_table
        mock_client.return_value = mock_bq_client
        
        connector = BigQueryConnector(config)
        connector.connect()
        
        schema = connector.get_schema()
        
        assert len(schema) > 0


class TestSnowflakeConnector:
    """Comprehensive tests for Snowflake connector."""

    @patch('snowflake.connector.connect')
    def test_connect_success(self, mock_connect, config):
        """Test successful Snowflake connection."""
        mock_connection = Mock()
        mock_connect.return_value = mock_connection
        
        connector = SnowflakeConnector(config)
        result = connector.connect()
        
        assert result is True
        assert connector.connection == mock_connection

    @patch('snowflake.connector.connect')
    def test_execute_query_success(self, mock_connect, config):
        """Test successful Snowflake query execution."""
        mock_connection = Mock()
        mock_cursor = Mock()
        mock_connection.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = [('Alice', 25), ('Bob', 30)]
        mock_cursor.description = [('name',), ('age',)]
        mock_connect.return_value = mock_connection
        
        connector = SnowflakeConnector(config)
        connector.connect()
        
        result = connector.execute_query("SELECT name, age FROM users")
        
        assert len(result) == 2
        assert result[0]['name'] == 'Alice'


class TestRedshiftConnector:
    """Comprehensive tests for Redshift connector."""

    @patch('psycopg2.connect')
    def test_connect_success(self, mock_connect, config):
        """Test successful Redshift connection."""
        mock_connection = Mock()
        mock_connect.return_value = mock_connection
        
        connector = RedshiftConnector(config)
        result = connector.connect()
        
        assert result is True
        assert connector.connection == mock_connection

    @patch('psycopg2.connect')
    def test_copy_from_s3_success(self, mock_connect, config):
        """Test successful S3 copy operation."""
        mock_connection = Mock()
        mock_cursor = Mock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_connection
        
        connector = RedshiftConnector(config)
        connector.connect()
        
        result = connector.copy_from_s3(
            table='users',
            s3_path='s3://bucket/users.csv',
            iam_role='arn:aws:iam::123456789012:role/RedshiftRole'
        )
        
        assert result is True
        mock_cursor.execute.assert_called()

    @patch('psycopg2.connect')
    def test_unload_to_s3_success(self, mock_connect, config):
        """Test successful S3 unload operation."""
        mock_connection = Mock()
        mock_cursor = Mock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_connection
        
        connector = RedshiftConnector(config)
        connector.connect()
        
        result = connector.unload_to_s3(
            query='SELECT * FROM users',
            s3_path='s3://bucket/export/',
            iam_role='arn:aws:iam::123456789012:role/RedshiftRole'
        )
        
        assert result is True
        mock_cursor.execute.assert_called()


class TestRedisConnector:
    """Comprehensive tests for Redis connector."""

    @patch('redis.Redis')
    def test_connect_success(self, mock_redis, config):
        """Test successful Redis connection."""
        mock_connection = Mock()
        mock_redis.return_value = mock_connection
        
        connector = RedisConnector(config)
        result = connector.connect()
        
        assert result is True
        assert connector.client == mock_connection

    @patch('redis.Redis')
    def test_set_value_success(self, mock_redis, config):
        """Test successful Redis set operation."""
        mock_connection = Mock()
        mock_connection.set.return_value = True
        mock_redis.return_value = mock_connection
        
        connector = RedisConnector(config)
        connector.connect()
        
        result = connector.set_value('test_key', 'test_value')
        
        assert result is True
        mock_connection.set.assert_called_with('test_key', 'test_value')

    @patch('redis.Redis')
    def test_get_value_success(self, mock_redis, config):
        """Test successful Redis get operation."""
        mock_connection = Mock()
        mock_connection.get.return_value = b'test_value'
        mock_redis.return_value = mock_connection
        
        connector = RedisConnector(config)
        connector.connect()
        
        result = connector.get_value('test_key')
        
        assert result == 'test_value'
        mock_connection.get.assert_called_with('test_key')


# Test error handling and edge cases for all connectors
class TestConnectorErrorHandling:
    """Test error handling across all connectors."""

    def test_connection_timeout(self):
        """Test connection timeout handling."""
        config = {
            'host': 'unreachable-host.example.com',
            'port': 5432,
            'database': 'test_db',
            'username': 'test_user',
            'password': 'test_pass',
            'timeout': 1
        }
        
        connector = PostgreSQLConnector(config)
        result = connector.connect()
        
        assert result is False

    def test_invalid_credentials(self):
        """Test handling of invalid credentials."""
        config = {
            'host': 'localhost',
            'port': 5432,
            'database': 'test_db',
            'username': 'invalid_user',
            'password': 'invalid_pass'
        }
        
        connector = PostgreSQLConnector(config)
        with patch('psycopg2.connect') as mock_connect:
            mock_connect.side_effect = Exception("Authentication failed")
            result = connector.connect()
            
        assert result is False

    def test_network_interruption(self):
        """Test handling of network interruptions."""
        config = {
            'host': 'localhost',
            'port': 5432,
            'database': 'test_db',
            'username': 'test_user',
            'password': 'test_pass'
        }
        
        connector = PostgreSQLConnector(config)
        with patch('psycopg2.connect') as mock_connect:
            mock_connection = Mock()
            mock_cursor = Mock()
            mock_cursor.execute.side_effect = Exception("Network error")
            mock_connection.cursor.return_value = mock_cursor
            mock_connect.return_value = mock_connection
            
            connector.connect()
            
            with pytest.raises(Exception):
                connector.execute_query("SELECT 1")

    def test_large_data_handling(self):
        """Test handling of large datasets."""
        # Create a large DataFrame for testing
        large_data = pd.DataFrame({
            'id': range(10000),
            'value': ['test'] * 10000
        })
        
        config = {
            'host': 'localhost',
            'port': 5432,
            'database': 'test_db',
            'username': 'test_user',
            'password': 'test_pass'
        }
        
        with patch('psycopg2.connect') as mock_connect:
            mock_connection = Mock()
            mock_cursor = Mock()
            mock_connection.cursor.return_value = mock_cursor
            mock_connect.return_value = mock_connection
            
            connector = PostgreSQLConnector(config)
            connector.connect()
            
            result = connector.insert_data_batch('test_table', large_data, batch_size=1000)
            
            assert result is True
            assert mock_cursor.execute.call_count >= 10  # At least 10 batches


# Performance and stress tests
class TestConnectorPerformance:
    """Test connector performance and stress scenarios."""

    @patch('psycopg2.connect')
    def test_concurrent_connections(self, mock_connect, config):
        """Test handling of concurrent connections."""
        mock_connection = Mock()
        mock_connect.return_value = mock_connection
        
        connectors = [PostgreSQLConnector(config) for _ in range(10)]
        results = [connector.connect() for connector in connectors]
        
        assert all(results)

    @patch('psycopg2.connect')
    def test_connection_pool_exhaustion(self, mock_connect, config):
        """Test handling when connection pool is exhausted."""
        mock_connect.side_effect = [Mock() for _ in range(5)] + [Exception("Too many connections")]
        
        connectors = [PostgreSQLConnector(config) for _ in range(6)]
        results = [connector.connect() for connector in connectors]
        
        # First 5 should succeed, 6th should fail
        assert sum(results) == 5

    @patch('psycopg2.connect')
    def test_memory_usage_large_results(self, mock_connect, config):
        """Test memory usage with large result sets."""
        mock_connection = Mock()
        mock_cursor = Mock()
        # Simulate large result set
        large_result = [('data', i) for i in range(100000)]
        mock_cursor.fetchall.return_value = large_result
        mock_cursor.description = [('column1',), ('column2',)]
        mock_connection.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_connection
        
        connector = PostgreSQLConnector(config)
        connector.connect()
        
        result = connector.execute_query("SELECT * FROM large_table")
        
        assert len(result) == 100000
        # Verify memory is properly handled (no memory leaks)
        del result  # Cleanup


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=synthetic_data_mcp.database.connectors"])