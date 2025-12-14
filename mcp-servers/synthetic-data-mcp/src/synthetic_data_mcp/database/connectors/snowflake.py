"""
Snowflake connector for cloud data warehouse operations.

Supports:
- Snowflake SQL API
- Multi-cluster warehouses
- Time travel queries
- Zero-copy cloning
- Secure data sharing
- JSON/semi-structured data
"""

import asyncio
import json
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, timedelta
from loguru import logger

try:
    import snowflake.connector
    from snowflake.connector import DictCursor
    from snowflake.connector.errors import Error as SnowflakeError
    import pandas as pd
except ImportError:
    snowflake = None
    DictCursor = None
    SnowflakeError = None
    pd = None
    logger.warning("Snowflake connector not installed - Snowflake connector disabled")

from ..base import CloudDatabaseConnector


class SnowflakeConnector(CloudDatabaseConnector):
    """Snowflake cloud data warehouse connector with advanced features."""
    
    def __init__(self, connection_config: Dict[str, Any]):
        """
        Initialize Snowflake connector.
        
        Args:
            connection_config: Snowflake connection parameters
                - account: Snowflake account identifier
                - user: Username
                - password: Password (optional if using key_pair auth)
                - private_key: Private key for key_pair authentication (optional)
                - database: Default database
                - schema: Default schema (default: PUBLIC)
                - warehouse: Compute warehouse (default: COMPUTE_WH)
                - role: User role (optional)
                - authenticator: Authentication method (default: snowflake)
                - session_parameters: Additional session parameters
        """
        if snowflake is None:
            raise ImportError("Snowflake connector required. Install with: pip install snowflake-connector-python pandas")
            
        super().__init__(connection_config)
        
        # Set defaults
        self.config.setdefault('schema', 'PUBLIC')
        self.config.setdefault('warehouse', 'COMPUTE_WH')
        self.config.setdefault('authenticator', 'snowflake')
        
        self.connection = None
    
    def _setup_authentication(self):
        """Setup Snowflake authentication."""
        # Key-pair authentication setup would go here if needed
        pass
    
    async def connect(self) -> bool:
        """Establish Snowflake connection."""
        try:
            # Build connection parameters
            connection_params = {
                'account': self.config['account'],
                'user': self.config['user'],
                'database': self.config['database'],
                'schema': self.config['schema'],
                'warehouse': self.config['warehouse'],
                'authenticator': self.config['authenticator']
            }
            
            # Add authentication
            if self.config.get('password'):
                connection_params['password'] = self.config['password']
            
            if self.config.get('private_key'):
                connection_params['private_key'] = self.config['private_key']
            
            if self.config.get('role'):
                connection_params['role'] = self.config['role']
            
            # Add session parameters
            if self.config.get('session_parameters'):
                connection_params['session_parameters'] = self.config['session_parameters']
            
            # Create connection
            self.connection = snowflake.connector.connect(**connection_params)
            
            # Test connection
            cursor = self.connection.cursor()
            cursor.execute("SELECT CURRENT_VERSION()")
            version = cursor.fetchone()[0]
            cursor.close()
            
            logger.info(f"Connected to Snowflake: {version}")
            self._connected = True
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to Snowflake: {e}")
            self._connected = False
            return False
    
    async def disconnect(self) -> None:
        """Close Snowflake connection."""
        if self.connection:
            self.connection.close()
            self.connection = None
        self._connected = False
        logger.info("Disconnected from Snowflake")
    
    async def execute_query(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Execute Snowflake SQL query."""
        if not self.connection:
            raise RuntimeError("Not connected to Snowflake")
        
        try:
            cursor = self.connection.cursor(DictCursor)
            
            if parameters:
                cursor.execute(query, parameters)
            else:
                cursor.execute(query)
            
            results = cursor.fetchall()
            cursor.close()
            
            # Convert Snowflake types to Python types
            converted_results = []
            for row in results:
                converted_row = {}
                for key, value in row.items():
                    if isinstance(value, datetime):
                        converted_row[key] = value.isoformat()
                    elif hasattr(value, 'isoformat'):  # Date objects
                        converted_row[key] = value.isoformat()
                    else:
                        converted_row[key] = value
                converted_results.append(converted_row)
            
            return converted_results
            
        except Exception as e:
            logger.error(f"Snowflake query failed: {e}")
            logger.error(f"Query: {query}")
            raise
    
    async def execute_write(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> int:
        """Execute Snowflake DML (INSERT, UPDATE, DELETE)."""
        if not self.connection:
            raise RuntimeError("Not connected to Snowflake")
        
        try:
            cursor = self.connection.cursor()
            
            if parameters:
                cursor.execute(query, parameters)
            else:
                cursor.execute(query)
            
            affected_rows = cursor.rowcount
            cursor.close()
            
            return affected_rows or 0
            
        except Exception as e:
            logger.error(f"Snowflake write operation failed: {e}")
            logger.error(f"Query: {query}")
            raise
    
    async def create_dataset(self, dataset_name: str, location: Optional[str] = None) -> bool:
        """Create Snowflake database."""
        try:
            create_sql = f"CREATE DATABASE IF NOT EXISTS {dataset_name}"
            
            if location:
                # In Snowflake, this would be handled by account region
                pass
            
            await self.execute_write(create_sql)
            logger.info(f"Created Snowflake database: {dataset_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create database {dataset_name}: {e}")
            return False
    
    async def create_table(self, table_name: str, schema: Dict[str, Any]) -> bool:
        """Create Snowflake table with schema."""
        try:
            columns = []
            
            for field_name, field_config in schema.items():
                if field_name == '_metadata':
                    continue
                
                column_def = self._build_column_definition(field_name, field_config)
                columns.append(column_def)
            
            # Add default timestamp columns
            columns.extend([
                "created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()",
                "updated_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()"
            ])
            
            # Build CREATE TABLE statement
            create_sql = f"""
                CREATE TABLE IF NOT EXISTS {table_name} (
                    id NUMBER AUTOINCREMENT START 1 INCREMENT 1,
                    {', '.join(columns)},
                    PRIMARY KEY (id)
                )
            """
            
            await self.execute_write(create_sql)
            
            # Create indexes if specified
            for field_name, field_config in schema.items():
                if field_config.get('index'):
                    index_sql = f"CREATE INDEX IF NOT EXISTS idx_{table_name}_{field_name} ON {table_name} ({field_name})"
                    await self.execute_write(index_sql)
            
            logger.info(f"Created Snowflake table: {table_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create table {table_name}: {e}")
            return False
    
    def _build_column_definition(self, field_name: str, field_config: Dict[str, Any]) -> str:
        """Build Snowflake column definition."""
        
        field_type = field_config.get('type', 'STRING')
        nullable = field_config.get('nullable', True)
        default = field_config.get('default')
        
        # Map Python types to Snowflake types
        type_mapping = {
            'str': 'VARCHAR(16777216)',
            'int': 'NUMBER',
            'float': 'FLOAT',
            'bool': 'BOOLEAN',
            'datetime': 'TIMESTAMP_NTZ',
            'date': 'DATE',
            'time': 'TIME',
            'json': 'VARIANT',
            'dict': 'OBJECT',
            'list': 'ARRAY',
            'binary': 'BINARY',
            'geography': 'GEOGRAPHY'
        }
        
        sf_type = type_mapping.get(field_type.lower(), 'VARCHAR(16777216)')
        
        # Handle specific length/precision
        if 'length' in field_config and field_type.lower() in ['str', 'varchar']:
            sf_type = f"VARCHAR({field_config['length']})"
        elif 'precision' in field_config and field_type.lower() in ['number', 'decimal']:
            precision = field_config['precision']
            scale = field_config.get('scale', 0)
            sf_type = f"NUMBER({precision},{scale})"
        
        # Build column definition
        column_def = f"{field_name} {sf_type}"
        
        if not nullable:
            column_def += " NOT NULL"
        
        if default is not None:
            if field_type.lower() in ['datetime', 'timestamp'] and default == 'now':
                column_def += " DEFAULT CURRENT_TIMESTAMP()"
            elif isinstance(default, str):
                column_def += f" DEFAULT '{default}'"
            else:
                column_def += f" DEFAULT {default}"
        
        return column_def
    
    async def insert_bulk(self, table_name: str, data: List[Dict[str, Any]]) -> int:
        """Efficient bulk insert using Snowflake COPY INTO or batch INSERT."""
        if not data:
            return 0
        
        try:
            # For smaller datasets, use batch INSERT
            if len(data) < 1000:
                return await self._batch_insert(table_name, data)
            
            # For larger datasets, use COPY INTO with staged data
            return await self._copy_insert(table_name, data)
            
        except Exception as e:
            logger.error(f"Bulk insert failed for {table_name}: {e}")
            raise
    
    async def _batch_insert(self, table_name: str, data: List[Dict[str, Any]]) -> int:
        """Insert data using batch INSERT statements."""
        if not data:
            return 0
        
        # Get column names
        columns = list(data[0].keys())
        column_names = ', '.join(columns)
        placeholders = ', '.join(['%s'] * len(columns))
        
        insert_sql = f"INSERT INTO {table_name} ({column_names}) VALUES ({placeholders})"
        
        cursor = self.connection.cursor()
        
        # Prepare data
        values_list = []
        for record in data:
            values = []
            for col in columns:
                value = record.get(col)
                if isinstance(value, (dict, list)):
                    values.append(json.dumps(value))
                else:
                    values.append(value)
            values_list.append(tuple(values))
        
        cursor.executemany(insert_sql, values_list)
        affected_rows = cursor.rowcount
        cursor.close()
        
        logger.info(f"Batch inserted {affected_rows} records into {table_name}")
        return affected_rows
    
    async def _copy_insert(self, table_name: str, data: List[Dict[str, Any]]) -> int:
        """Insert data using COPY INTO from staged files."""
        # This would require staging data to Snowflake internal stage
        # For now, fall back to batch insert
        return await self._batch_insert(table_name, data)
    
    async def upload_data(self, table_name: str, data: List[Dict[str, Any]], dataset_name: Optional[str] = None) -> int:
        """Upload data using PUT and COPY INTO commands."""
        try:
            # Create temporary stage
            stage_name = f"temp_stage_{int(datetime.now().timestamp())}"
            
            cursor = self.connection.cursor()
            
            # Create temporary stage
            cursor.execute(f"CREATE TEMPORARY STAGE {stage_name}")
            
            # Convert data to CSV or JSON for staging
            df = pd.DataFrame(data)
            temp_file = f"/tmp/{table_name}_{int(datetime.now().timestamp())}.csv"
            df.to_csv(temp_file, index=False)
            
            # PUT file to stage
            cursor.execute(f"PUT file://{temp_file} @{stage_name}")
            
            # COPY INTO table
            copy_sql = f"""
                COPY INTO {table_name}
                FROM @{stage_name}
                FILE_FORMAT = (TYPE = CSV SKIP_HEADER = 1)
            """
            cursor.execute(copy_sql)
            
            # Clean up
            cursor.execute(f"DROP STAGE {stage_name}")
            cursor.close()
            
            import os
            os.unlink(temp_file)
            
            logger.info(f"Uploaded {len(data)} records to {table_name}")
            return len(data)
            
        except Exception as e:
            logger.error(f"Data upload failed for {table_name}: {e}")
            raise
    
    async def get_table_schema(self, table_name: str) -> Dict[str, Any]:
        """Get Snowflake table schema and metadata."""
        try:
            # Get column information
            describe_sql = f"DESCRIBE TABLE {table_name}"
            columns_info = await self.execute_query(describe_sql)
            
            # Get table information
            show_sql = f"SHOW TABLES LIKE '{table_name}'"
            table_info = await self.execute_query(show_sql)
            
            schema_fields = {}
            for col in columns_info:
                schema_fields[col['name']] = {
                    'type': col['type'],
                    'nullable': col['null?'] == 'Y',
                    'default': col['default'],
                    'primary_key': col['primary key'] == 'Y',
                    'unique_key': col['unique key'] == 'Y'
                }
            
            table_metadata = table_info[0] if table_info else {}
            
            return {
                'table_name': table_name,
                'schema': schema_fields,
                'created_on': table_metadata.get('created_on'),
                'database_name': table_metadata.get('database_name'),
                'schema_name': table_metadata.get('schema_name'),
                'kind': table_metadata.get('kind'),
                'comment': table_metadata.get('comment'),
                'cluster_by': table_metadata.get('cluster_by'),
                'rows': table_metadata.get('rows'),
                'bytes': table_metadata.get('bytes')
            }
            
        except Exception as e:
            logger.error(f"Failed to get schema for {table_name}: {e}")
            return {}
    
    async def list_tables(self) -> List[str]:
        """List all tables in current database/schema."""
        try:
            tables_info = await self.execute_query("SHOW TABLES")
            return [table['name'] for table in tables_info]
        except Exception as e:
            logger.error(f"Failed to list tables: {e}")
            return []
    
    async def time_travel_query(self, table_name: str, timestamp: datetime, query: str) -> List[Dict[str, Any]]:
        """Execute time travel query."""
        try:
            time_travel_sql = query.replace(table_name, f"{table_name} AT (TIMESTAMP => '{timestamp.isoformat()}')")
            return await self.execute_query(time_travel_sql)
        except Exception as e:
            logger.error(f"Time travel query failed: {e}")
            raise
    
    async def clone_table(self, source_table: str, target_table: str, at_timestamp: Optional[datetime] = None) -> bool:
        """Create zero-copy clone of table."""
        try:
            if at_timestamp:
                clone_sql = f"CREATE TABLE {target_table} CLONE {source_table} AT (TIMESTAMP => '{at_timestamp.isoformat()}')"
            else:
                clone_sql = f"CREATE TABLE {target_table} CLONE {source_table}"
            
            await self.execute_write(clone_sql)
            logger.info(f"Cloned table {source_table} to {target_table}")
            return True
            
        except Exception as e:
            logger.error(f"Table clone failed: {e}")
            return False
    
    async def create_warehouse(self, warehouse_name: str, size: str = 'X-SMALL', auto_suspend: int = 60) -> bool:
        """Create compute warehouse."""
        try:
            create_sql = f"""
                CREATE WAREHOUSE IF NOT EXISTS {warehouse_name}
                WITH WAREHOUSE_SIZE = '{size}'
                AUTO_SUSPEND = {auto_suspend}
                AUTO_RESUME = TRUE
            """
            
            await self.execute_write(create_sql)
            logger.info(f"Created warehouse: {warehouse_name}")
            return True
            
        except Exception as e:
            logger.error(f"Warehouse creation failed: {e}")
            return False
    
    async def use_warehouse(self, warehouse_name: str) -> bool:
        """Switch to different warehouse."""
        try:
            await self.execute_write(f"USE WAREHOUSE {warehouse_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to use warehouse {warehouse_name}: {e}")
            return False
    
    async def health_check(self) -> Dict[str, Any]:
        """Comprehensive health check."""
        try:
            start_time = datetime.now()
            
            # Basic connectivity test
            version_info = await self.execute_query("SELECT CURRENT_VERSION() as version")
            
            # Performance test
            query_start = datetime.now()
            await self.execute_query("SELECT 1 as test")
            query_time = (datetime.now() - query_start).total_seconds()
            
            # Get account/session info
            account_info = await self.execute_query("""
                SELECT 
                    CURRENT_ACCOUNT() as account,
                    CURRENT_DATABASE() as database,
                    CURRENT_SCHEMA() as schema,
                    CURRENT_WAREHOUSE() as warehouse,
                    CURRENT_USER() as user,
                    CURRENT_ROLE() as role
            """)
            
            # Get warehouse info
            warehouse_info = await self.execute_query("SHOW WAREHOUSES")
            current_warehouse = next((wh for wh in warehouse_info if wh['name'] == account_info[0]['warehouse']), {})
            
            # Count tables
            tables = await self.execute_query("SHOW TABLES")
            
            health_check_time = (datetime.now() - start_time).total_seconds()
            
            return {
                'status': 'healthy',
                'version': version_info[0]['version'],
                'account': account_info[0]['account'],
                'database': account_info[0]['database'],
                'schema': account_info[0]['schema'],
                'warehouse': account_info[0]['warehouse'],
                'warehouse_size': current_warehouse.get('size'),
                'warehouse_state': current_warehouse.get('state'),
                'user': account_info[0]['user'],
                'role': account_info[0]['role'],
                'table_count': len(tables),
                'query_response_time_ms': query_time * 1000,
                'health_check_time_ms': health_check_time * 1000,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }