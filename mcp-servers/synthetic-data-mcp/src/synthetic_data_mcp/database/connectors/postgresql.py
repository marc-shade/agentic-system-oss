"""
PostgreSQL connector with advanced features for production use.

Supports:
- Connection pooling with asyncpg
- Advanced indexing (GIN, GiST, BRIN)
- JSON/JSONB operations
- Full-text search
- Partitioning support
- Performance optimization
- Backup and recovery
"""

import asyncio
import json
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, timedelta
from loguru import logger

try:
    import asyncpg
    from asyncpg import Pool, Connection
    from asyncpg.pool import PoolConnectionProxy
except ImportError:
    asyncpg = None
    Pool = None
    Connection = None
    PoolConnectionProxy = None
    logger.warning("asyncpg not installed - PostgreSQL connector disabled")

from ..base import RelationalDatabaseConnector


class PostgreSQLConnector(RelationalDatabaseConnector):
    """High-performance PostgreSQL connector with enterprise features."""
    
    def __init__(self, connection_config: Dict[str, Any]):
        """
        Initialize PostgreSQL connector.
        
        Args:
            connection_config: PostgreSQL connection parameters
                - host: Database host
                - port: Database port (default: 5432)
                - database: Database name
                - user: Username
                - password: Password
                - ssl: SSL mode (disable/allow/prefer/require/verify-ca/verify-full)
                - pool_min_size: Minimum pool connections (default: 10)
                - pool_max_size: Maximum pool connections (default: 100)
                - command_timeout: Query timeout in seconds (default: 60)
        """
        if asyncpg is None:
            raise ImportError("asyncpg is required for PostgreSQL connector. Install with: pip install asyncpg")
            
        super().__init__(connection_config)
        
        # Set defaults
        self.config.setdefault('port', 5432)
        self.config.setdefault('ssl', 'prefer')
        self.config.setdefault('pool_min_size', 10)
        self.config.setdefault('pool_max_size', 100)
        self.config.setdefault('command_timeout', 60)
        
        self.pool: Optional[Pool] = None
        self._current_transaction = None
    
    async def connect(self) -> bool:
        """Establish PostgreSQL connection pool."""
        try:
            # Build connection string
            dsn = (
                f"postgresql://{self.config['user']}:{self.config['password']}"
                f"@{self.config['host']}:{self.config['port']}/{self.config['database']}"
                f"?sslmode={self.config['ssl']}"
            )
            
            # Create connection pool
            self.pool = await asyncpg.create_pool(
                dsn,
                min_size=self.config['pool_min_size'],
                max_size=self.config['pool_max_size'],
                command_timeout=self.config['command_timeout'],
                server_settings={
                    'jit': 'off',  # Disable JIT for better predictability
                    'application_name': 'synthetic-data-mcp'
                }
            )
            
            # Test connection
            async with self.pool.acquire() as conn:
                version = await conn.fetchval('SELECT version()')
                logger.info(f"Connected to PostgreSQL: {version}")
            
            self._connected = True
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {e}")
            self._connected = False
            return False
    
    async def disconnect(self) -> None:
        """Close PostgreSQL connection pool."""
        if self.pool:
            await self.pool.close()
            self.pool = None
        self._connected = False
        logger.info("Disconnected from PostgreSQL")
    
    @asynccontextmanager
    async def get_connection(self):
        """Get connection from pool."""
        if not self.pool:
            raise RuntimeError("Not connected to database")
        
        async with self.pool.acquire() as conn:
            yield conn
    
    async def execute_query(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Execute SELECT query and return results."""
        async with self.get_connection() as conn:
            try:
                if parameters:
                    # Convert named parameters to positional for asyncpg
                    param_list = []
                    query_converted = query
                    for key, value in parameters.items():
                        param_list.append(value)
                        query_converted = query_converted.replace(f":{key}", f"${len(param_list)}")
                    
                    rows = await conn.fetch(query_converted, *param_list)
                else:
                    rows = await conn.fetch(query)
                
                # Convert to list of dicts
                results = [dict(row) for row in rows]
                return results
                
            except Exception as e:
                logger.error(f"Query execution failed: {e}")
                logger.error(f"Query: {query}")
                logger.error(f"Parameters: {parameters}")
                raise
    
    async def execute_write(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> int:
        """Execute INSERT, UPDATE, or DELETE query."""
        async with self.get_connection() as conn:
            try:
                if parameters:
                    # Convert named parameters to positional
                    param_list = []
                    query_converted = query
                    for key, value in parameters.items():
                        param_list.append(value)
                        query_converted = query_converted.replace(f":{key}", f"${len(param_list)}")
                    
                    result = await conn.execute(query_converted, *param_list)
                else:
                    result = await conn.execute(query)
                
                # Extract number of affected rows from result
                if result.startswith('INSERT'):
                    return int(result.split()[-1])
                elif result.startswith('UPDATE') or result.startswith('DELETE'):
                    return int(result.split()[-1])
                else:
                    return 0
                    
            except Exception as e:
                logger.error(f"Write operation failed: {e}")
                logger.error(f"Query: {query}")
                logger.error(f"Parameters: {parameters}")
                raise
    
    async def create_table(self, table_name: str, schema: Dict[str, Any]) -> bool:
        """Create table with PostgreSQL-specific optimizations."""
        try:
            columns = []
            indexes = []
            constraints = []
            
            for field_name, field_config in schema.items():
                if field_name == '_metadata':
                    continue
                
                column_def = self._build_column_definition(field_name, field_config)
                columns.append(column_def)
                
                # Add indexes
                if field_config.get('index'):
                    indexes.append(f"CREATE INDEX IF NOT EXISTS idx_{table_name}_{field_name} ON {table_name} ({field_name})")
                
                if field_config.get('unique'):
                    constraints.append(f"UNIQUE ({field_name})")
            
            # Build CREATE TABLE statement
            create_sql = f"""
                CREATE TABLE IF NOT EXISTS {table_name} (
                    id SERIAL PRIMARY KEY,
                    {', '.join(columns)},
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    updated_at TIMESTAMPTZ DEFAULT NOW()
                    {', ' + ', '.join(constraints) if constraints else ''}
                )
            """
            
            # Execute table creation
            await self.execute_write(create_sql)
            
            # Create indexes
            for index_sql in indexes:
                await self.execute_write(index_sql)
            
            # Create update trigger for updated_at
            trigger_sql = f"""
                CREATE OR REPLACE FUNCTION update_modified_column()
                RETURNS TRIGGER AS $$
                BEGIN
                    NEW.updated_at = NOW();
                    RETURN NEW;
                END;
                $$ language 'plpgsql';
                
                DROP TRIGGER IF EXISTS update_{table_name}_modtime ON {table_name};
                CREATE TRIGGER update_{table_name}_modtime 
                    BEFORE UPDATE ON {table_name} 
                    FOR EACH ROW EXECUTE FUNCTION update_modified_column();
            """
            
            await self.execute_write(trigger_sql)
            
            logger.info(f"Created PostgreSQL table: {table_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create table {table_name}: {e}")
            return False
    
    def _build_column_definition(self, field_name: str, field_config: Dict[str, Any]) -> str:
        """Build PostgreSQL column definition."""
        
        field_type = field_config.get('type', 'TEXT')
        nullable = field_config.get('nullable', True)
        default = field_config.get('default')
        
        # Map Python types to PostgreSQL types
        type_mapping = {
            'str': 'TEXT',
            'int': 'INTEGER',
            'float': 'DOUBLE PRECISION',
            'bool': 'BOOLEAN',
            'datetime': 'TIMESTAMPTZ',
            'date': 'DATE',
            'json': 'JSONB',
            'uuid': 'UUID',
            'email': 'TEXT',
            'url': 'TEXT',
            'phone': 'TEXT'
        }
        
        pg_type = type_mapping.get(field_type.lower(), field_type.upper())
        
        # Build column definition
        column_def = f"{field_name} {pg_type}"
        
        if not nullable:
            column_def += " NOT NULL"
        
        if default is not None:
            if isinstance(default, str):
                column_def += f" DEFAULT '{default}'"
            else:
                column_def += f" DEFAULT {default}"
        
        return column_def
    
    async def insert_bulk(self, table_name: str, data: List[Dict[str, Any]]) -> int:
        """Efficient bulk insert using PostgreSQL COPY."""
        if not data:
            return 0
        
        try:
            # Get table schema
            schema_info = await self.get_table_schema(table_name)
            columns = [col for col in schema_info['columns'].keys() if col not in ['id', 'created_at', 'updated_at']]
            
            # Prepare data for COPY
            records = []
            for record in data:
                row = []
                for col in columns:
                    value = record.get(col)
                    if value is None:
                        row.append(None)
                    elif isinstance(value, (dict, list)):
                        row.append(json.dumps(value))
                    else:
                        row.append(value)
                records.append(tuple(row))
            
            # Use COPY for efficient bulk insert
            async with self.get_connection() as conn:
                await conn.copy_records_to_table(
                    table_name,
                    records=records,
                    columns=columns
                )
            
            logger.info(f"Bulk inserted {len(records)} records into {table_name}")
            return len(records)
            
        except Exception as e:
            logger.error(f"Bulk insert failed for {table_name}: {e}")
            raise
    
    async def get_table_schema(self, table_name: str) -> Dict[str, Any]:
        """Get comprehensive table schema information."""
        
        schema_query = """
            SELECT 
                column_name,
                data_type,
                is_nullable,
                column_default,
                character_maximum_length,
                numeric_precision,
                numeric_scale
            FROM information_schema.columns 
            WHERE table_name = $1
            ORDER BY ordinal_position
        """
        
        index_query = """
            SELECT 
                indexname,
                indexdef
            FROM pg_indexes 
            WHERE tablename = $1
        """
        
        constraint_query = """
            SELECT 
                constraint_name,
                constraint_type
            FROM information_schema.table_constraints
            WHERE table_name = $1
        """
        
        async with self.get_connection() as conn:
            # Get columns
            columns = {}
            rows = await conn.fetch(schema_query, table_name)
            
            for row in rows:
                columns[row['column_name']] = {
                    'type': row['data_type'],
                    'nullable': row['is_nullable'] == 'YES',
                    'default': row['column_default'],
                    'max_length': row['character_maximum_length'],
                    'precision': row['numeric_precision'],
                    'scale': row['numeric_scale']
                }
            
            # Get indexes
            indexes = {}
            rows = await conn.fetch(index_query, table_name)
            for row in rows:
                indexes[row['indexname']] = row['indexdef']
            
            # Get constraints
            constraints = {}
            rows = await conn.fetch(constraint_query, table_name)
            for row in rows:
                constraints[row['constraint_name']] = row['constraint_type']
            
            return {
                'columns': columns,
                'indexes': indexes,
                'constraints': constraints,
                'table_name': table_name
            }
    
    async def list_tables(self) -> List[str]:
        """List all tables in the database."""
        query = """
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        """
        
        result = await self.execute_query(query)
        return [row['table_name'] for row in result]
    
    async def begin_transaction(self):
        """Begin database transaction."""
        if self._current_transaction:
            raise RuntimeError("Transaction already in progress")
        
        conn = await self.pool.acquire()
        transaction = conn.transaction()
        await transaction.start()
        
        self._current_transaction = {
            'connection': conn,
            'transaction': transaction
        }
    
    async def commit_transaction(self):
        """Commit current transaction."""
        if not self._current_transaction:
            raise RuntimeError("No transaction in progress")
        
        try:
            await self._current_transaction['transaction'].commit()
        finally:
            await self.pool.release(self._current_transaction['connection'])
            self._current_transaction = None
    
    async def rollback_transaction(self):
        """Rollback current transaction."""
        if not self._current_transaction:
            raise RuntimeError("No transaction in progress")
        
        try:
            await self._current_transaction['transaction'].rollback()
        finally:
            await self.pool.release(self._current_transaction['connection'])
            self._current_transaction = None
    
    async def create_full_text_index(self, table_name: str, columns: List[str], language: str = 'english') -> bool:
        """Create full-text search index."""
        try:
            # Create GIN index for full-text search
            column_list = ', '.join(columns)
            index_name = f"fts_idx_{table_name}_{'_'.join(columns)}"
            
            create_index_sql = f"""
                CREATE INDEX IF NOT EXISTS {index_name} 
                ON {table_name} 
                USING gin(to_tsvector('{language}', {column_list}))
            """
            
            await self.execute_write(create_index_sql)
            logger.info(f"Created full-text search index: {index_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create full-text index: {e}")
            return False
    
    async def search_full_text(self, table_name: str, columns: List[str], query: str, language: str = 'english', limit: int = 100) -> List[Dict[str, Any]]:
        """Perform full-text search."""
        column_list = ', '.join(columns)
        
        search_sql = f"""
            SELECT *, ts_rank(to_tsvector('{language}', {column_list}), to_tsquery('{language}', $1)) as rank
            FROM {table_name}
            WHERE to_tsvector('{language}', {column_list}) @@ to_tsquery('{language}', $1)
            ORDER BY rank DESC
            LIMIT $2
        """
        
        async with self.get_connection() as conn:
            rows = await conn.fetch(search_sql, query, limit)
            return [dict(row) for row in rows]
    
    async def create_partition(self, parent_table: str, partition_name: str, partition_key: str, start_value: Any, end_value: Any) -> bool:
        """Create table partition."""
        try:
            partition_sql = f"""
                CREATE TABLE IF NOT EXISTS {partition_name} 
                PARTITION OF {parent_table}
                FOR VALUES FROM ('{start_value}') TO ('{end_value}')
            """
            
            await self.execute_write(partition_sql)
            logger.info(f"Created partition {partition_name} for {parent_table}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create partition: {e}")
            return False
    
    async def optimize_table(self, table_name: str) -> Dict[str, Any]:
        """Optimize table performance."""
        try:
            # VACUUM and ANALYZE
            await self.execute_write(f"VACUUM ANALYZE {table_name}")
            
            # Get table statistics
            stats_query = f"""
                SELECT 
                    schemaname,
                    tablename,
                    n_live_tup,
                    n_dead_tup,
                    last_vacuum,
                    last_analyze
                FROM pg_stat_user_tables 
                WHERE tablename = '{table_name}'
            """
            
            stats = await self.execute_query(stats_query)
            
            return {
                'optimized': True,
                'stats': stats[0] if stats else {},
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to optimize table {table_name}: {e}")
            return {'optimized': False, 'error': str(e)}
    
    async def health_check(self) -> Dict[str, Any]:
        """Comprehensive health check."""
        try:
            start_time = datetime.now()
            
            async with self.get_connection() as conn:
                # Check connection
                version = await conn.fetchval('SELECT version()')
                
                # Check performance
                query_start = datetime.now()
                await conn.fetchval('SELECT 1')
                query_time = (datetime.now() - query_start).total_seconds()
                
                # Get database stats
                db_stats = await conn.fetchrow("""
                    SELECT 
                        pg_database_size(current_database()) as db_size,
                        (SELECT count(*) FROM pg_stat_activity WHERE state = 'active') as active_connections,
                        current_setting('max_connections')::int as max_connections
                """)
                
                # Get table count
                table_count = await conn.fetchval("""
                    SELECT count(*) FROM information_schema.tables 
                    WHERE table_schema = 'public'
                """)
            
            health_check_time = (datetime.now() - start_time).total_seconds()
            
            return {
                'status': 'healthy',
                'version': version.split('\n')[0],
                'database_size_bytes': db_stats['db_size'],
                'active_connections': db_stats['active_connections'],
                'max_connections': db_stats['max_connections'],
                'connection_utilization': db_stats['active_connections'] / db_stats['max_connections'],
                'query_response_time_ms': query_time * 1000,
                'health_check_time_ms': health_check_time * 1000,
                'table_count': table_count,
                'pool_size': self.pool.get_size() if self.pool else 0,
                'pool_idle': self.pool.get_idle_size() if self.pool else 0,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    async def backup_table(self, table_name: str, backup_path: str) -> bool:
        """Create table backup using pg_dump equivalent."""
        try:
            # This would need to interface with pg_dump or implement custom backup
            # For now, export as JSON
            data = await self.execute_query(f"SELECT * FROM {table_name}")
            schema = await self.get_table_schema(table_name)
            
            backup_data = {
                'table_name': table_name,
                'backup_timestamp': datetime.now().isoformat(),
                'schema': schema,
                'data': data,
                'record_count': len(data)
            }
            
            import aiofiles
            async with aiofiles.open(backup_path, 'w') as f:
                await f.write(json.dumps(backup_data, indent=2, default=str))
            
            logger.info(f"Backed up table {table_name} to {backup_path}")
            return True
            
        except Exception as e:
            logger.error(f"Backup failed for {table_name}: {e}")
            return False