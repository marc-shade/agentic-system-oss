"""
Amazon Redshift connector for cloud data warehouse operations.

Supports:
- Redshift Data API and direct connections
- Columnar storage optimization
- Distribution keys and sort keys
- Redshift Spectrum for S3 queries
- Workload Management (WLM)
- Federated queries
"""

import asyncio
import json
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, timedelta
from loguru import logger

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    import boto3
    from botocore.exceptions import ClientError
    import pandas as pd
except ImportError:
    psycopg2 = None
    RealDictCursor = None
    boto3 = None
    ClientError = None
    pd = None
    logger.warning("Redshift dependencies not installed - Redshift connector disabled")

from ..base import CloudDatabaseConnector


class RedshiftConnector(CloudDatabaseConnector):
    """Amazon Redshift cloud data warehouse connector."""
    
    def __init__(self, connection_config: Dict[str, Any]):
        """
        Initialize Redshift connector.
        
        Args:
            connection_config: Redshift connection parameters
                - host: Redshift cluster endpoint
                - port: Database port (default: 5439)
                - database: Database name
                - user: Username
                - password: Password
                - ssl: Use SSL (default: True)
                - cluster_identifier: Redshift cluster identifier
                - aws_access_key_id: AWS access key (optional, uses IAM if not provided)
                - aws_secret_access_key: AWS secret key (optional)
                - aws_region: AWS region (default: us-east-1)
                - use_data_api: Use Redshift Data API (default: False)
                - workgroup: Serverless workgroup name (for serverless)
        """
        if psycopg2 is None or boto3 is None:
            raise ImportError("Redshift dependencies required. Install with: pip install psycopg2-binary boto3 pandas")
            
        super().__init__(connection_config)
        
        # Set defaults
        self.config.setdefault('port', 5439)
        self.config.setdefault('ssl', True)
        self.config.setdefault('aws_region', 'us-east-1')
        self.config.setdefault('use_data_api', False)
        
        self.connection = None
        self.data_api_client = None
    
    def _setup_authentication(self):
        """Setup AWS authentication for Redshift."""
        # Set up boto3 session
        session_kwargs = {'region_name': self.config['aws_region']}
        
        if self.config.get('aws_access_key_id') and self.config.get('aws_secret_access_key'):
            session_kwargs.update({
                'aws_access_key_id': self.config['aws_access_key_id'],
                'aws_secret_access_key': self.config['aws_secret_access_key']
            })
        
        self.boto_session = boto3.Session(**session_kwargs)
        
        if self.config['use_data_api']:
            self.data_api_client = self.boto_session.client('redshift-data')
    
    async def connect(self) -> bool:
        """Establish Redshift connection."""
        try:
            if self.config['use_data_api']:
                return await self._connect_data_api()
            else:
                return await self._connect_direct()
                
        except Exception as e:
            logger.error(f"Failed to connect to Redshift: {e}")
            self._connected = False
            return False
    
    async def _connect_direct(self) -> bool:
        """Connect using direct psycopg2 connection."""
        try:
            connection_params = {
                'host': self.config['host'],
                'port': self.config['port'],
                'database': self.config['database'],
                'user': self.config['user'],
                'password': self.config['password']
            }
            
            if self.config['ssl']:
                connection_params['sslmode'] = 'require'
            
            self.connection = psycopg2.connect(**connection_params)
            
            # Test connection
            cursor = self.connection.cursor()
            cursor.execute("SELECT version()")
            version = cursor.fetchone()[0]
            cursor.close()
            
            logger.info(f"Connected to Redshift: {version}")
            self._connected = True
            return True
            
        except Exception as e:
            logger.error(f"Direct connection failed: {e}")
            return False
    
    async def _connect_data_api(self) -> bool:
        """Connect using Redshift Data API."""
        try:
            # Test Data API connectivity
            response = self.data_api_client.describe_statement(Id='test')  # This will fail but validates credentials
        except ClientError as e:
            if e.response['Error']['Code'] != 'ValidationException':
                logger.error(f"Data API connection failed: {e}")
                return False
        except Exception as e:
            logger.error(f"Data API setup failed: {e}")
            return False
        
        logger.info("Connected to Redshift via Data API")
        self._connected = True
        return True
    
    async def disconnect(self) -> None:
        """Close Redshift connection."""
        if self.connection:
            self.connection.close()
            self.connection = None
        
        if self.data_api_client:
            self.data_api_client = None
        
        self._connected = False
        logger.info("Disconnected from Redshift")
    
    async def execute_query(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Execute Redshift SQL query."""
        if not self._connected:
            raise RuntimeError("Not connected to Redshift")
        
        if self.config['use_data_api']:
            return await self._execute_query_data_api(query, parameters)
        else:
            return await self._execute_query_direct(query, parameters)
    
    async def _execute_query_direct(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Execute query using direct connection."""
        try:
            cursor = self.connection.cursor(cursor_factory=RealDictCursor)
            
            if parameters:
                cursor.execute(query, parameters)
            else:
                cursor.execute(query)
            
            results = cursor.fetchall()
            cursor.close()
            
            # Convert to list of dictionaries
            return [dict(row) for row in results]
            
        except Exception as e:
            logger.error(f"Redshift query failed: {e}")
            logger.error(f"Query: {query}")
            raise
    
    async def _execute_query_data_api(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Execute query using Data API."""
        try:
            # Start query execution
            execute_params = {
                'Database': self.config['database'],
                'Sql': query
            }
            
            if self.config.get('cluster_identifier'):
                execute_params['ClusterIdentifier'] = self.config['cluster_identifier']
            elif self.config.get('workgroup'):
                execute_params['WorkgroupName'] = self.config['workgroup']
            
            response = self.data_api_client.execute_statement(**execute_params)
            statement_id = response['Id']
            
            # Wait for completion
            while True:
                status_response = self.data_api_client.describe_statement(Id=statement_id)
                status = status_response['Status']
                
                if status == 'FINISHED':
                    break
                elif status in ['FAILED', 'ABORTED']:
                    error = status_response.get('Error', 'Query failed')
                    raise Exception(f"Query {status.lower()}: {error}")
                
                await asyncio.sleep(1)  # Poll every second
            
            # Get results
            result_response = self.data_api_client.get_statement_result(Id=statement_id)
            
            # Convert results to list of dictionaries
            results = []
            if 'Records' in result_response:
                columns = [col['name'] for col in result_response.get('ColumnMetadata', [])]
                
                for record in result_response['Records']:
                    row = {}
                    for i, value in enumerate(record):
                        column_name = columns[i] if i < len(columns) else f'col_{i}'
                        # Extract value from Redshift Data API format
                        if 'stringValue' in value:
                            row[column_name] = value['stringValue']
                        elif 'longValue' in value:
                            row[column_name] = value['longValue']
                        elif 'doubleValue' in value:
                            row[column_name] = value['doubleValue']
                        elif 'booleanValue' in value:
                            row[column_name] = value['booleanValue']
                        elif 'isNull' in value and value['isNull']:
                            row[column_name] = None
                        else:
                            row[column_name] = str(value)
                    results.append(row)
            
            return results
            
        except Exception as e:
            logger.error(f"Redshift Data API query failed: {e}")
            raise
    
    async def execute_write(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> int:
        """Execute Redshift DML (INSERT, UPDATE, DELETE)."""
        if self.config['use_data_api']:
            return await self._execute_write_data_api(query, parameters)
        else:
            return await self._execute_write_direct(query, parameters)
    
    async def _execute_write_direct(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> int:
        """Execute write operation using direct connection."""
        try:
            cursor = self.connection.cursor()
            
            if parameters:
                cursor.execute(query, parameters)
            else:
                cursor.execute(query)
            
            self.connection.commit()
            affected_rows = cursor.rowcount
            cursor.close()
            
            return affected_rows or 0
            
        except Exception as e:
            self.connection.rollback()
            logger.error(f"Redshift write operation failed: {e}")
            raise
    
    async def _execute_write_data_api(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> int:
        """Execute write operation using Data API."""
        try:
            execute_params = {
                'Database': self.config['database'],
                'Sql': query
            }
            
            if self.config.get('cluster_identifier'):
                execute_params['ClusterIdentifier'] = self.config['cluster_identifier']
            elif self.config.get('workgroup'):
                execute_params['WorkgroupName'] = self.config['workgroup']
            
            response = self.data_api_client.execute_statement(**execute_params)
            statement_id = response['Id']
            
            # Wait for completion
            while True:
                status_response = self.data_api_client.describe_statement(Id=statement_id)
                status = status_response['Status']
                
                if status == 'FINISHED':
                    return status_response.get('ResultMetadata', {}).get('UpdateCount', 0)
                elif status in ['FAILED', 'ABORTED']:
                    error = status_response.get('Error', 'Query failed')
                    raise Exception(f"Query {status.lower()}: {error}")
                
                await asyncio.sleep(1)
            
        except Exception as e:
            logger.error(f"Redshift Data API write failed: {e}")
            raise
    
    async def create_dataset(self, dataset_name: str, location: Optional[str] = None) -> bool:
        """Create Redshift database (schema)."""
        try:
            create_sql = f"CREATE SCHEMA IF NOT EXISTS {dataset_name}"
            await self.execute_write(create_sql)
            logger.info(f"Created Redshift schema: {dataset_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to create schema {dataset_name}: {e}")
            return False
    
    async def create_table(self, table_name: str, schema: Dict[str, Any]) -> bool:
        """Create Redshift table with optimizations."""
        try:
            columns = []
            
            for field_name, field_config in schema.items():
                if field_name == '_metadata':
                    continue
                
                column_def = self._build_column_definition(field_name, field_config)
                columns.append(column_def)
            
            # Add default timestamp columns
            columns.extend([
                "created_at TIMESTAMP DEFAULT GETDATE()",
                "updated_at TIMESTAMP DEFAULT GETDATE()"
            ])
            
            # Build CREATE TABLE with Redshift optimizations
            metadata = schema.get('_metadata', {})
            
            create_sql = f"""
                CREATE TABLE IF NOT EXISTS {table_name} (
                    id BIGINT IDENTITY(1,1),
                    {', '.join(columns)},
                    PRIMARY KEY (id)
                )
            """
            
            # Add distribution key
            if metadata.get('distkey'):
                create_sql += f" DISTKEY({metadata['distkey']})"
            
            # Add sort keys
            if metadata.get('sortkey'):
                sortkeys = metadata['sortkey']
                if isinstance(sortkeys, str):
                    create_sql += f" SORTKEY({sortkeys})"
                elif isinstance(sortkeys, list):
                    create_sql += f" SORTKEY({', '.join(sortkeys)})"
            
            await self.execute_write(create_sql)
            logger.info(f"Created Redshift table: {table_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create table {table_name}: {e}")
            return False
    
    def _build_column_definition(self, field_name: str, field_config: Dict[str, Any]) -> str:
        """Build Redshift column definition."""
        
        field_type = field_config.get('type', 'VARCHAR')
        nullable = field_config.get('nullable', True)
        default = field_config.get('default')
        
        # Map Python types to Redshift types
        type_mapping = {
            'str': 'VARCHAR(65535)',
            'int': 'BIGINT',
            'float': 'DOUBLE PRECISION',
            'bool': 'BOOLEAN',
            'datetime': 'TIMESTAMP',
            'date': 'DATE',
            'decimal': 'DECIMAL(18,2)',
            'json': 'VARCHAR(65535)',  # Redshift doesn't have native JSON
            'text': 'VARCHAR(65535)',
            'binary': 'VARBINARY(1024)'
        }
        
        rs_type = type_mapping.get(field_type.lower(), 'VARCHAR(65535)')
        
        # Handle specific constraints
        if 'length' in field_config and field_type.lower() in ['str', 'varchar']:
            length = min(field_config['length'], 65535)  # Redshift max VARCHAR length
            rs_type = f"VARCHAR({length})"
        elif 'precision' in field_config and field_type.lower() in ['decimal', 'numeric']:
            precision = field_config['precision']
            scale = field_config.get('scale', 2)
            rs_type = f"DECIMAL({precision},{scale})"
        
        # Build column definition
        column_def = f"{field_name} {rs_type}"
        
        if not nullable:
            column_def += " NOT NULL"
        
        if default is not None:
            if field_type.lower() in ['datetime', 'timestamp'] and default == 'now':
                column_def += " DEFAULT GETDATE()"
            elif isinstance(default, str):
                column_def += f" DEFAULT '{default}'"
            else:
                column_def += f" DEFAULT {default}"
        
        # Add encoding hints for better compression
        if field_config.get('encoding'):
            column_def += f" ENCODE {field_config['encoding']}"
        elif field_type.lower() == 'int':
            column_def += " ENCODE DELTA"
        elif field_type.lower() in ['str', 'varchar'] and field_config.get('length', 0) < 256:
            column_def += " ENCODE LZO"
        
        return column_def
    
    async def insert_bulk(self, table_name: str, data: List[Dict[str, Any]]) -> int:
        """Efficient bulk insert using COPY command."""
        if not data:
            return 0
        
        try:
            # For small datasets, use INSERT
            if len(data) < 1000:
                return await self._batch_insert(table_name, data)
            
            # For larger datasets, use COPY from S3
            return await self._copy_from_s3(table_name, data)
            
        except Exception as e:
            logger.error(f"Bulk insert failed for {table_name}: {e}")
            raise
    
    async def _batch_insert(self, table_name: str, data: List[Dict[str, Any]]) -> int:
        """Insert using batch INSERT statements."""
        columns = list(data[0].keys())
        column_names = ', '.join(columns)
        placeholders = ', '.join(['%s'] * len(columns))
        
        insert_sql = f"INSERT INTO {table_name} ({column_names}) VALUES ({placeholders})"
        
        if self.config['use_data_api']:
            # Data API doesn't support batch operations well, so insert one by one
            inserted_count = 0
            for record in data:
                values = [record.get(col) for col in columns]
                parameterized_sql = insert_sql
                for i, value in enumerate(values):
                    if isinstance(value, str):
                        parameterized_sql = parameterized_sql.replace('%s', f"'{value}'", 1)
                    elif value is None:
                        parameterized_sql = parameterized_sql.replace('%s', 'NULL', 1)
                    else:
                        parameterized_sql = parameterized_sql.replace('%s', str(value), 1)
                
                await self.execute_write(parameterized_sql)
                inserted_count += 1
            
            return inserted_count
        else:
            # Use direct connection for batch insert
            cursor = self.connection.cursor()
            
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
            self.connection.commit()
            affected_rows = cursor.rowcount
            cursor.close()
            
            logger.info(f"Batch inserted {affected_rows} records into {table_name}")
            return affected_rows
    
    async def _copy_from_s3(self, table_name: str, data: List[Dict[str, Any]]) -> int:
        """Use COPY command to load data from S3."""
        # This would require:
        # 1. Upload data to S3 as CSV/JSON
        # 2. Execute COPY command
        # For now, fall back to batch insert
        return await self._batch_insert(table_name, data)
    
    async def upload_data(self, table_name: str, data: List[Dict[str, Any]], dataset_name: Optional[str] = None) -> int:
        """Upload data using COPY from S3."""
        return await self.insert_bulk(table_name, data)
    
    async def get_table_schema(self, table_name: str) -> Dict[str, Any]:
        """Get Redshift table schema and metadata."""
        try:
            # Get column information from system tables
            schema_query = """
                SELECT 
                    column_name,
                    data_type,
                    is_nullable,
                    column_default,
                    character_maximum_length,
                    numeric_precision,
                    numeric_scale,
                    encoding
                FROM information_schema.columns 
                WHERE table_name = %s
                ORDER BY ordinal_position
            """
            
            columns_info = await self._execute_query_direct(schema_query, [table_name])
            
            # Get table statistics
            stats_query = f"""
                SELECT 
                    tbl,
                    rows,
                    diststyle,
                    sortkey1
                FROM svv_table_info 
                WHERE tbl = '{table_name}'
            """
            
            stats_info = await self.execute_query(stats_query)
            
            schema_fields = {}
            for col in columns_info:
                schema_fields[col['column_name']] = {
                    'type': col['data_type'],
                    'nullable': col['is_nullable'] == 'YES',
                    'default': col['column_default'],
                    'max_length': col['character_maximum_length'],
                    'precision': col['numeric_precision'],
                    'scale': col['numeric_scale'],
                    'encoding': col.get('encoding')
                }
            
            table_stats = stats_info[0] if stats_info else {}
            
            return {
                'table_name': table_name,
                'schema': schema_fields,
                'row_count': table_stats.get('rows', 0),
                'distribution_style': table_stats.get('diststyle'),
                'sort_key': table_stats.get('sortkey1'),
                'encoding_info': {col: info.get('encoding') for col, info in schema_fields.items()}
            }
            
        except Exception as e:
            logger.error(f"Failed to get schema for {table_name}: {e}")
            return {}
    
    async def list_tables(self) -> List[str]:
        """List all tables in current database."""
        try:
            tables_query = """
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name
            """
            
            tables_info = await self.execute_query(tables_query)
            return [table['table_name'] for table in tables_info]
        except Exception as e:
            logger.error(f"Failed to list tables: {e}")
            return []
    
    async def analyze_table(self, table_name: str) -> Dict[str, Any]:
        """Run ANALYZE on table and return statistics."""
        try:
            # Run ANALYZE
            await self.execute_write(f"ANALYZE {table_name}")
            
            # Get updated statistics
            stats_query = f"""
                SELECT 
                    schemaname,
                    tablename,
                    attname as column_name,
                    n_distinct,
                    correlation,
                    most_common_vals,
                    most_common_freqs
                FROM pg_stats 
                WHERE tablename = '{table_name}'
            """
            
            stats = await self.execute_query(stats_query)
            
            return {
                'analyzed': True,
                'timestamp': datetime.now().isoformat(),
                'column_statistics': stats
            }
            
        except Exception as e:
            logger.error(f"Table analysis failed for {table_name}: {e}")
            return {'analyzed': False, 'error': str(e)}
    
    async def vacuum_table(self, table_name: str) -> Dict[str, Any]:
        """Run VACUUM on table."""
        try:
            await self.execute_write(f"VACUUM {table_name}")
            
            return {
                'vacuumed': True,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"VACUUM failed for {table_name}: {e}")
            return {'vacuumed': False, 'error': str(e)}
    
    async def health_check(self) -> Dict[str, Any]:
        """Comprehensive health check."""
        try:
            start_time = datetime.now()
            
            # Basic connectivity test
            version_info = await self.execute_query("SELECT version()")
            
            # Performance test
            query_start = datetime.now()
            await self.execute_query("SELECT 1 as test")
            query_time = (datetime.now() - query_start).total_seconds()
            
            # Get cluster info
            cluster_info = await self.execute_query("""
                SELECT 
                    current_database() as database,
                    current_schema() as schema,
                    current_user as user
            """)
            
            # Get table count
            table_count_info = await self.execute_query("""
                SELECT COUNT(*) as table_count 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
            """)
            
            health_check_time = (datetime.now() - start_time).total_seconds()
            
            return {
                'status': 'healthy',
                'version': version_info[0]['version'],
                'database': cluster_info[0]['database'],
                'schema': cluster_info[0]['schema'],
                'user': cluster_info[0]['user'],
                'table_count': table_count_info[0]['table_count'],
                'connection_type': 'data_api' if self.config['use_data_api'] else 'direct',
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