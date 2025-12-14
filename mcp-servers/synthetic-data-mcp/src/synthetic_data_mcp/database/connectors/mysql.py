"""
MySQL connector with full MySQL 8.0 support and optimization features.

Supports:
- Connection pooling with aiomysql
- MySQL 8.0 specific features (JSON, CTEs, window functions)
- InnoDB optimization
- Replication support
- Performance monitoring
"""

import asyncio
import json
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, timedelta
from loguru import logger

try:
    import aiomysql
    from aiomysql import Pool, Connection
except ImportError:
    aiomysql = None
    Pool = None
    Connection = None
    logger.warning("aiomysql not installed - MySQL connector disabled")

from ..base import RelationalDatabaseConnector


class MySQLConnector(RelationalDatabaseConnector):
    """High-performance MySQL connector with MySQL 8.0 features."""
    
    def __init__(self, connection_config: Dict[str, Any]):
        """
        Initialize MySQL connector.
        
        Args:
            connection_config: MySQL connection parameters
                - host: Database host
                - port: Database port (default: 3306)
                - database: Database name
                - user: Username
                - password: Password
                - charset: Character set (default: utf8mb4)
                - use_unicode: Use unicode (default: True)
                - pool_minsize: Minimum pool connections (default: 10)
                - pool_maxsize: Maximum pool connections (default: 100)
                - pool_recycle: Connection recycle time in seconds (default: 3600)
                - autocommit: Auto-commit mode (default: False)
        """
        if aiomysql is None:
            raise ImportError("aiomysql is required for MySQL connector. Install with: pip install aiomysql")
            
        super().__init__(connection_config)
        
        # Set defaults
        self.config.setdefault('port', 3306)
        self.config.setdefault('charset', 'utf8mb4')
        self.config.setdefault('use_unicode', True)
        self.config.setdefault('pool_minsize', 10)
        self.config.setdefault('pool_maxsize', 100)
        self.config.setdefault('pool_recycle', 3600)
        self.config.setdefault('autocommit', False)
        
        self.pool: Optional[Pool] = None
        self._current_transaction = None
    
    async def connect(self) -> bool:
        """Establish MySQL connection pool."""
        try:
            # Create connection pool
            self.pool = await aiomysql.create_pool(
                host=self.config['host'],
                port=self.config['port'],
                user=self.config['user'],
                password=self.config['password'],
                db=self.config['database'],
                charset=self.config['charset'],
                use_unicode=self.config['use_unicode'],
                autocommit=self.config['autocommit'],
                minsize=self.config['pool_minsize'],
                maxsize=self.config['pool_maxsize'],
                pool_recycle=self.config['pool_recycle'],
                echo=False
            )
            
            # Test connection and get version
            async with self.pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute('SELECT VERSION()')
                    version = await cursor.fetchone()
                    logger.info(f"Connected to MySQL: {version[0]}")
            
            self._connected = True
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to MySQL: {e}")
            self._connected = False
            return False
    
    async def disconnect(self) -> None:
        """Close MySQL connection pool."""
        if self.pool:
            self.pool.close()
            await self.pool.wait_closed()
            self.pool = None
        self._connected = False
        logger.info("Disconnected from MySQL")
    
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
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                try:
                    if parameters:
                        await cursor.execute(query, parameters)
                    else:
                        await cursor.execute(query)
                    
                    results = await cursor.fetchall()
                    return list(results) if results else []
                    
                except Exception as e:
                    logger.error(f"Query execution failed: {e}")
                    logger.error(f"Query: {query}")
                    logger.error(f"Parameters: {parameters}")
                    raise
    
    async def execute_write(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> int:
        """Execute INSERT, UPDATE, or DELETE query."""
        async with self.get_connection() as conn:
            async with conn.cursor() as cursor:
                try:
                    if parameters:
                        await cursor.execute(query, parameters)
                    else:
                        await cursor.execute(query)
                    
                    await conn.commit()
                    return cursor.rowcount
                    
                except Exception as e:
                    await conn.rollback()
                    logger.error(f"Write operation failed: {e}")
                    logger.error(f"Query: {query}")
                    logger.error(f"Parameters: {parameters}")
                    raise
    
    async def create_table(self, table_name: str, schema: Dict[str, Any]) -> bool:
        """Create table with MySQL-specific optimizations."""
        try:
            columns = []
            indexes = []
            
            for field_name, field_config in schema.items():
                if field_name == '_metadata':
                    continue
                
                column_def = self._build_column_definition(field_name, field_config)
                columns.append(column_def)
                
                # Add indexes
                if field_config.get('index'):
                    index_type = field_config.get('index_type', 'BTREE')
                    indexes.append(f"INDEX idx_{table_name}_{field_name} ({field_name}) USING {index_type}")
                
                if field_config.get('unique'):
                    indexes.append(f"UNIQUE KEY uk_{table_name}_{field_name} ({field_name})")
                
                if field_config.get('fulltext'):
                    indexes.append(f"FULLTEXT KEY ft_{table_name}_{field_name} ({field_name})")
            
            # Build CREATE TABLE statement with MySQL optimizations
            create_sql = f"""
                CREATE TABLE IF NOT EXISTS {table_name} (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    {', '.join(columns)},
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                    {', ' + ', '.join(indexes) if indexes else ''}
                ) ENGINE=InnoDB 
                  DEFAULT CHARSET=utf8mb4 
                  COLLATE=utf8mb4_unicode_ci
                  ROW_FORMAT=DYNAMIC
            """
            
            await self.execute_write(create_sql)
            logger.info(f"Created MySQL table: {table_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create table {table_name}: {e}")
            return False
    
    def _build_column_definition(self, field_name: str, field_config: Dict[str, Any]) -> str:
        """Build MySQL column definition."""
        
        field_type = field_config.get('type', 'TEXT')
        nullable = field_config.get('nullable', True)
        default = field_config.get('default')
        
        # Map Python types to MySQL types
        type_mapping = {
            'str': 'VARCHAR(255)',
            'text': 'TEXT',
            'longtext': 'LONGTEXT',
            'int': 'INT',
            'bigint': 'BIGINT',
            'float': 'DOUBLE',
            'decimal': 'DECIMAL(10,2)',
            'bool': 'BOOLEAN',
            'datetime': 'TIMESTAMP',
            'date': 'DATE',
            'time': 'TIME',
            'json': 'JSON',
            'uuid': 'CHAR(36)',
            'email': 'VARCHAR(255)',
            'url': 'TEXT',
            'phone': 'VARCHAR(20)'
        }
        
        mysql_type = type_mapping.get(field_type.lower(), 'VARCHAR(255)')
        
        # Handle length specification
        if 'length' in field_config and field_type.lower() in ['str', 'varchar']:
            mysql_type = f"VARCHAR({field_config['length']})"
        elif 'precision' in field_config and field_type.lower() == 'decimal':
            precision = field_config['precision']
            scale = field_config.get('scale', 2)
            mysql_type = f"DECIMAL({precision},{scale})"
        
        # Build column definition
        column_def = f"{field_name} {mysql_type}"
        
        if not nullable:
            column_def += " NOT NULL"
        
        if default is not None:
            if field_type.lower() in ['datetime', 'timestamp'] and default == 'now':
                column_def += " DEFAULT CURRENT_TIMESTAMP"
            elif isinstance(default, str):
                column_def += f" DEFAULT '{default}'"
            else:
                column_def += f" DEFAULT {default}"
        
        return column_def
    
    async def insert_bulk(self, table_name: str, data: List[Dict[str, Any]]) -> int:
        """Efficient bulk insert using MySQL INSERT ... VALUES."""
        if not data:
            return 0
        
        try:
            # Get column names from first record
            columns = list(data[0].keys())
            column_names = ', '.join(columns)
            placeholders = ', '.join(['%s'] * len(columns))
            
            # Prepare values
            values = []
            for record in data:
                row = []
                for col in columns:
                    value = record.get(col)
                    if isinstance(value, (dict, list)):
                        row.append(json.dumps(value))
                    else:
                        row.append(value)
                values.append(tuple(row))
            
            # Build bulk insert query
            insert_sql = f"""
                INSERT INTO {table_name} ({column_names})
                VALUES ({placeholders})
            """
            
            async with self.get_connection() as conn:
                async with conn.cursor() as cursor:
                    await cursor.executemany(insert_sql, values)
                    await conn.commit()
                    
                    inserted_count = cursor.rowcount
            
            logger.info(f"Bulk inserted {inserted_count} records into {table_name}")
            return inserted_count
            
        except Exception as e:
            logger.error(f"Bulk insert failed for {table_name}: {e}")
            raise
    
    async def get_table_schema(self, table_name: str) -> Dict[str, Any]:
        """Get comprehensive table schema information."""
        
        schema_query = """
            SELECT 
                COLUMN_NAME,
                DATA_TYPE,
                IS_NULLABLE,
                COLUMN_DEFAULT,
                CHARACTER_MAXIMUM_LENGTH,
                NUMERIC_PRECISION,
                NUMERIC_SCALE,
                COLUMN_KEY,
                EXTRA
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
            ORDER BY ORDINAL_POSITION
        """
        
        index_query = """
            SELECT 
                INDEX_NAME,
                COLUMN_NAME,
                NON_UNIQUE,
                INDEX_TYPE
            FROM INFORMATION_SCHEMA.STATISTICS
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
            ORDER BY INDEX_NAME, SEQ_IN_INDEX
        """
        
        # Get columns
        columns = {}
        column_results = await self.execute_query(schema_query, {'table_schema': self.config['database'], 'table_name': table_name})
        
        for row in column_results:
            columns[row['COLUMN_NAME']] = {
                'type': row['DATA_TYPE'],
                'nullable': row['IS_NULLABLE'] == 'YES',
                'default': row['COLUMN_DEFAULT'],
                'max_length': row['CHARACTER_MAXIMUM_LENGTH'],
                'precision': row['NUMERIC_PRECISION'],
                'scale': row['NUMERIC_SCALE'],
                'key': row['COLUMN_KEY'],
                'extra': row['EXTRA']
            }
        
        # Get indexes
        indexes = {}
        index_results = await self.execute_query(index_query, {'table_schema': self.config['database'], 'table_name': table_name})
        
        for row in index_results:
            index_name = row['INDEX_NAME']
            if index_name not in indexes:
                indexes[index_name] = {
                    'columns': [],
                    'unique': row['NON_UNIQUE'] == 0,
                    'type': row['INDEX_TYPE']
                }
            indexes[index_name]['columns'].append(row['COLUMN_NAME'])
        
        return {
            'columns': columns,
            'indexes': indexes,
            'table_name': table_name
        }
    
    async def list_tables(self) -> List[str]:
        """List all tables in the database."""
        query = """
            SELECT TABLE_NAME 
            FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_SCHEMA = %s
            ORDER BY TABLE_NAME
        """
        
        result = await self.execute_query(query, {'table_schema': self.config['database']})
        return [row['TABLE_NAME'] for row in result]
    
    async def begin_transaction(self):
        """Begin database transaction."""
        if self._current_transaction:
            raise RuntimeError("Transaction already in progress")
        
        conn = await self.pool.acquire()
        await conn.begin()
        
        self._current_transaction = conn
    
    async def commit_transaction(self):
        """Commit current transaction."""
        if not self._current_transaction:
            raise RuntimeError("No transaction in progress")
        
        try:
            await self._current_transaction.commit()
        finally:
            self.pool.release(self._current_transaction)
            self._current_transaction = None
    
    async def rollback_transaction(self):
        """Rollback current transaction."""
        if not self._current_transaction:
            raise RuntimeError("No transaction in progress")
        
        try:
            await self._current_transaction.rollback()
        finally:
            self.pool.release(self._current_transaction)
            self._current_transaction = None
    
    async def create_json_index(self, table_name: str, column_name: str, json_path: str) -> bool:
        """Create index on JSON field path (MySQL 8.0+)."""
        try:
            index_name = f"idx_{table_name}_{column_name}_{json_path.replace('.', '_').replace('[', '_').replace(']', '')}"
            
            create_index_sql = f"""
                CREATE INDEX {index_name} 
                ON {table_name} ((JSON_EXTRACT({column_name}, '{json_path}')))
            """
            
            await self.execute_write(create_index_sql)
            logger.info(f"Created JSON index: {index_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create JSON index: {e}")
            return False
    
    async def search_json(self, table_name: str, column_name: str, json_path: str, value: Any, limit: int = 100) -> List[Dict[str, Any]]:
        """Search JSON column by path and value."""
        search_sql = f"""
            SELECT * 
            FROM {table_name}
            WHERE JSON_EXTRACT({column_name}, %s) = %s
            LIMIT %s
        """
        
        return await self.execute_query(search_sql, {'json_path': json_path, 'value': value, 'limit': limit})
    
    async def create_fulltext_index(self, table_name: str, columns: List[str]) -> bool:
        """Create MySQL FULLTEXT index."""
        try:
            column_list = ', '.join(columns)
            index_name = f"ft_idx_{table_name}_{'_'.join(columns)}"
            
            create_index_sql = f"""
                CREATE FULLTEXT INDEX {index_name} 
                ON {table_name} ({column_list})
            """
            
            await self.execute_write(create_index_sql)
            logger.info(f"Created fulltext index: {index_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create fulltext index: {e}")
            return False
    
    async def search_fulltext(self, table_name: str, columns: List[str], query: str, mode: str = 'NATURAL LANGUAGE', limit: int = 100) -> List[Dict[str, Any]]:
        """Perform MySQL FULLTEXT search."""
        column_list = ', '.join(columns)
        
        search_sql = f"""
            SELECT *, MATCH({column_list}) AGAINST (%s IN {mode} MODE) as relevance
            FROM {table_name}
            WHERE MATCH({column_list}) AGAINST (%s IN {mode} MODE)
            ORDER BY relevance DESC
            LIMIT %s
        """
        
        return await self.execute_query(search_sql, {'query1': query, 'query2': query, 'limit': limit})
    
    async def optimize_table(self, table_name: str) -> Dict[str, Any]:
        """Optimize table using MySQL OPTIMIZE TABLE."""
        try:
            # OPTIMIZE TABLE
            await self.execute_write(f"OPTIMIZE TABLE {table_name}")
            
            # Get table statistics
            stats_query = f"""
                SELECT 
                    table_name,
                    table_rows,
                    data_length,
                    index_length,
                    data_free,
                    auto_increment,
                    create_time,
                    update_time
                FROM information_schema.tables 
                WHERE table_schema = %s AND table_name = %s
            """
            
            stats = await self.execute_query(stats_query, {'table_schema': self.config['database'], 'table_name': table_name})
            
            return {
                'optimized': True,
                'stats': stats[0] if stats else {},
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to optimize table {table_name}: {e}")
            return {'optimized': False, 'error': str(e)}
    
    async def analyze_performance(self, table_name: Optional[str] = None) -> Dict[str, Any]:
        """Analyze database/table performance."""
        try:
            performance_data = {}
            
            # Global status
            global_status = await self.execute_query("SHOW GLOBAL STATUS WHERE Variable_name IN ('Queries', 'Questions', 'Slow_queries', 'Connections')")
            performance_data['global_status'] = {row['Variable_name']: row['Value'] for row in global_status}
            
            # InnoDB status
            innodb_status = await self.execute_query("SHOW ENGINE INNODB STATUS")
            performance_data['innodb_status'] = innodb_status[0]['Status'] if innodb_status else ""
            
            # Process list
            process_list = await self.execute_query("SHOW PROCESSLIST")
            performance_data['active_connections'] = len([p for p in process_list if p['Command'] != 'Sleep'])
            
            if table_name:
                # Table-specific analysis
                table_status = await self.execute_query(f"SHOW TABLE STATUS LIKE '{table_name}'")
                if table_status:
                    performance_data['table_status'] = table_status[0]
                
                # Index usage
                index_usage = await self.execute_query(f"""
                    SELECT 
                        INDEX_NAME,
                        CARDINALITY,
                        PACKED,
                        INDEX_TYPE
                    FROM INFORMATION_SCHEMA.STATISTICS
                    WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
                """, {'table_schema': self.config['database'], 'table_name': table_name})
                performance_data['index_usage'] = index_usage
            
            return performance_data
            
        except Exception as e:
            logger.error(f"Performance analysis failed: {e}")
            return {'error': str(e)}
    
    async def health_check(self) -> Dict[str, Any]:
        """Comprehensive health check."""
        try:
            start_time = datetime.now()
            
            async with self.get_connection() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cursor:
                    # Check connection and get version
                    await cursor.execute('SELECT VERSION() as version')
                    version_info = await cursor.fetchone()
                    
                    # Performance test
                    query_start = datetime.now()
                    await cursor.execute('SELECT 1')
                    await cursor.fetchone()
                    query_time = (datetime.now() - query_start).total_seconds()
                    
                    # Get database stats
                    await cursor.execute("""
                        SELECT 
                            (SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = %s) as table_count,
                            (SELECT VARIABLE_VALUE FROM information_schema.global_status WHERE VARIABLE_NAME = 'Threads_connected') as active_connections,
                            (SELECT @@max_connections) as max_connections,
                            (SELECT SUM(data_length + index_length) FROM information_schema.tables WHERE table_schema = %s) as db_size
                    """, (self.config['database'], self.config['database']))
                    
                    db_stats = await cursor.fetchone()
            
            health_check_time = (datetime.now() - start_time).total_seconds()
            
            return {
                'status': 'healthy',
                'version': version_info['version'],
                'database_size_bytes': db_stats['db_size'] or 0,
                'active_connections': int(db_stats['active_connections']),
                'max_connections': int(db_stats['max_connections']),
                'connection_utilization': int(db_stats['active_connections']) / int(db_stats['max_connections']),
                'query_response_time_ms': query_time * 1000,
                'health_check_time_ms': health_check_time * 1000,
                'table_count': int(db_stats['table_count']),
                'pool_size': self.pool.size if self.pool else 0,
                'pool_free': self.pool.freesize if self.pool else 0,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }