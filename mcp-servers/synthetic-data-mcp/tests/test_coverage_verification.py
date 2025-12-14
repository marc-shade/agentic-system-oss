"""
Coverage verification test to ensure connector modules are properly imported and tested.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock


def test_postgresql_connector_import_and_basic_execution():
    """Test PostgreSQL connector can be imported and basic methods work."""
    
    # First patch the dependencies, then import
    with patch('synthetic_data_mcp.database.connectors.postgresql.asyncpg') as mock_asyncpg:
        # Import after patching to ensure the code runs
        from synthetic_data_mcp.database.connectors.postgresql import PostgreSQLConnector
        
        # Test initialization path
        config = {
            'host': 'localhost',
            'port': 5432,
            'database': 'test_db',
            'user': 'test_user',
            'password': 'test_pass'
        }
        
        # This should execute the __init__ method
        connector = PostgreSQLConnector(config)
        
        # Verify defaults were set (this exercises the initialization code)
        assert connector.config['port'] == 5432
        assert connector.config['ssl'] == 'prefer'
        assert connector.config['pool_min_size'] == 10
        assert connector.config['pool_max_size'] == 100
        assert connector.pool is None
        
        # Test column definition building (pure method, no external deps)
        field_config = {'type': 'str', 'nullable': False, 'default': 'test'}
        result = connector._build_column_definition('name', field_config)
        assert 'TEXT NOT NULL' in result
        assert "DEFAULT 'test'" in result


def test_mysql_connector_import_and_basic_execution():
    """Test MySQL connector import and basic functionality."""
    
    with patch('synthetic_data_mcp.database.connectors.mysql.aiomysql') as mock_aiomysql:
        from synthetic_data_mcp.database.connectors.mysql import MySQLConnector
        
        config = {
            'host': 'localhost',
            'port': 3306,
            'database': 'test_db',
            'user': 'test_user',
            'password': 'test_pass'
        }
        
        connector = MySQLConnector(config)
        
        # Verify defaults
        assert connector.config['port'] == 3306
        assert connector.config['charset'] == 'utf8mb4'
        assert connector.config['use_unicode'] is True
        
        # Test column building
        field_config = {'type': 'str', 'length': 100, 'nullable': False}
        result = connector._build_column_definition('name', field_config)
        assert 'VARCHAR(100)' in result
        assert 'NOT NULL' in result


def test_mongodb_connector_import_and_basic_execution():
    """Test MongoDB connector import and basic functionality."""
    
    with patch('synthetic_data_mcp.database.connectors.mongodb.motor') as mock_motor:
        from synthetic_data_mcp.database.connectors.mongodb import MongoDBConnector
        
        config = {'database': 'test_db'}
        connector = MongoDBConnector(config)
        
        # Verify defaults
        assert connector.config['host'] == 'localhost'
        assert connector.config['port'] == 27017
        assert connector.config['auth_source'] == 'admin'
        
        # Test JSON schema building
        schema = {
            'name': {'type': 'str', 'min_length': 1, 'nullable': False},
            'age': {'type': 'int', 'nullable': True}
        }
        result = connector._build_json_schema(schema)
        
        assert result['type'] == 'object'
        assert 'properties' in result
        assert result['properties']['name']['type'] == 'string'
        assert result['properties']['name']['minLength'] == 1
        assert 'name' in result['required']
        assert 'age' not in result['required']


def test_bigquery_connector_import_and_basic_execution():
    """Test BigQuery connector import and basic functionality."""
    
    with patch('synthetic_data_mcp.database.connectors.bigquery.bigquery') as mock_bq:
        with patch('synthetic_data_mcp.database.connectors.bigquery.service_account') as mock_sa:
            from synthetic_data_mcp.database.connectors.bigquery import BigQueryConnector
            
            config = {'project_id': 'test-project'}
            connector = BigQueryConnector(config)
            
            # Verify defaults
            assert connector.config['location'] == 'US'
            assert connector.config['timeout'] == 300
            assert connector.config['dry_run'] is False
            
            # Test type mapping
            assert connector._map_to_bigquery_type('str') == 'STRING'
            assert connector._map_to_bigquery_type('int') == 'INT64'
            assert connector._map_to_bigquery_type('unknown') == 'STRING'


def test_snowflake_connector_import_and_basic_execution():
    """Test Snowflake connector import and basic functionality."""
    
    with patch('synthetic_data_mcp.database.connectors.snowflake.snowflake') as mock_sf:
        from synthetic_data_mcp.database.connectors.snowflake import SnowflakeConnector
        
        config = {
            'account': 'test-account',
            'user': 'test_user',
            'password': 'test_pass',
            'database': 'TEST_DB'
        }
        connector = SnowflakeConnector(config)
        
        # Verify defaults
        assert connector.config['schema'] == 'PUBLIC'
        assert connector.config['warehouse'] == 'COMPUTE_WH'
        assert connector.config['authenticator'] == 'snowflake'
        
        # Test column building
        field_config = {'type': 'decimal', 'precision': 10, 'scale': 2, 'nullable': False}
        result = connector._build_column_definition('amount', field_config)
        assert 'NUMBER(10,2)' in result
        assert 'NOT NULL' in result


def test_redshift_connector_import_and_basic_execution():
    """Test Redshift connector import and basic functionality."""
    
    with patch('synthetic_data_mcp.database.connectors.redshift.psycopg2') as mock_psycopg2:
        with patch('synthetic_data_mcp.database.connectors.redshift.boto3') as mock_boto3:
            from synthetic_data_mcp.database.connectors.redshift import RedshiftConnector
            
            config = {
                'host': 'test-cluster.abc123.us-west-2.redshift.amazonaws.com',
                'database': 'test_db',
                'user': 'test_user',
                'password': 'test_pass',
                'aws_region': 'us-west-2',
                'use_data_api': False  # Fix missing key error
            }
            connector = RedshiftConnector(config)
            
            # Verify defaults and config
            assert connector.config['port'] == 5439
            assert connector.config['ssl'] is True
            assert connector.config['aws_region'] == 'us-west-2'  # Match provided config
            
            # Test column building with encoding
            field_config = {'type': 'str', 'length': 50}
            result = connector._build_column_definition('code', field_config)
            assert 'VARCHAR(50)' in result
            assert 'ENCODE LZO' in result


@pytest.mark.asyncio
async def test_postgresql_async_methods():
    """Test PostgreSQL async methods with proper mocking."""
    
    with patch('synthetic_data_mcp.database.connectors.postgresql.asyncpg') as mock_asyncpg:
        from synthetic_data_mcp.database.connectors.postgresql import PostgreSQLConnector
        
        config = {'host': 'localhost', 'database': 'test', 'user': 'test', 'password': 'test'}
        connector = PostgreSQLConnector(config)
        
        # Test connect failure path
        mock_asyncpg.create_pool.side_effect = Exception("Connection failed")
        result = await connector.connect()
        assert result is False
        assert connector._connected is False
        
        # Test disconnect with no pool
        await connector.disconnect()  # Should not raise exception
        assert connector._connected is False


@pytest.mark.asyncio
async def test_mongodb_async_methods():
    """Test MongoDB async methods with proper mocking."""
    
    with patch('synthetic_data_mcp.database.connectors.mongodb.motor') as mock_motor:
        from synthetic_data_mcp.database.connectors.mongodb import MongoDBConnector
        
        config = {'database': 'test_db'}
        connector = MongoDBConnector(config)
        
        # Test connect failure
        mock_motor.motor_asyncio.AsyncIOMotorClient.side_effect = Exception("Connection failed")
        result = await connector.connect()
        assert result is False
        assert connector._connected is False


def test_import_all_connectors():
    """Test that all connector modules can be imported successfully."""
    
    # Test imports with proper patching
    with patch('synthetic_data_mcp.database.connectors.postgresql.asyncpg'):
        from synthetic_data_mcp.database.connectors.postgresql import PostgreSQLConnector
        assert PostgreSQLConnector is not None
    
    with patch('synthetic_data_mcp.database.connectors.mysql.aiomysql'):
        from synthetic_data_mcp.database.connectors.mysql import MySQLConnector
        assert MySQLConnector is not None
    
    with patch('synthetic_data_mcp.database.connectors.mongodb.motor'):
        from synthetic_data_mcp.database.connectors.mongodb import MongoDBConnector
        assert MongoDBConnector is not None
    
    with patch('synthetic_data_mcp.database.connectors.bigquery.bigquery'):
        with patch('synthetic_data_mcp.database.connectors.bigquery.service_account'):
            from synthetic_data_mcp.database.connectors.bigquery import BigQueryConnector
            assert BigQueryConnector is not None
    
    with patch('synthetic_data_mcp.database.connectors.snowflake.snowflake'):
        from synthetic_data_mcp.database.connectors.snowflake import SnowflakeConnector
        assert SnowflakeConnector is not None
    
    with patch('synthetic_data_mcp.database.connectors.redshift.psycopg2'):
        with patch('synthetic_data_mcp.database.connectors.redshift.boto3'):
            from synthetic_data_mcp.database.connectors.redshift import RedshiftConnector
            assert RedshiftConnector is not None