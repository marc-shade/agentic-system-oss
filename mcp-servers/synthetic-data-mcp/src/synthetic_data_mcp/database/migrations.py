"""
Database migration system for schema evolution and data migration.

Supports:
- Cross-database migrations (SQLite to PostgreSQL, etc.)
- Schema versioning and rollbacks
- Data transformation and validation
- Batch processing for large datasets
- Backup and recovery
"""

import asyncio
import json
import sqlite3
from typing import Any, Dict, List, Optional, Union, Callable
from datetime import datetime, timedelta
from pathlib import Path
from loguru import logger
from dataclasses import dataclass, asdict
from enum import Enum

from .manager import DatabaseManager, DatabaseType, DatabaseRole
from .base import DatabaseConnector


class MigrationStatus(Enum):
    """Migration execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


@dataclass
class Migration:
    """Migration definition."""
    id: str
    name: str
    version: str
    description: str
    source_db_type: DatabaseType
    target_db_type: DatabaseType
    up_sql: str
    down_sql: str
    data_transformations: List[Dict[str, Any]]
    dependencies: List[str]
    created_at: str
    status: MigrationStatus = MigrationStatus.PENDING
    executed_at: Optional[str] = None
    execution_time_seconds: Optional[float] = None
    error_message: Optional[str] = None


class MigrationManager:
    """Manages database schema and data migrations."""
    
    def __init__(self, database_manager: DatabaseManager, migrations_path: str = "migrations/"):
        """
        Initialize migration manager.
        
        Args:
            database_manager: Database manager instance
            migrations_path: Directory containing migration files
        """
        self.db_manager = database_manager
        self.migrations_path = Path(migrations_path)
        self.migrations_path.mkdir(exist_ok=True)
        
        # Migration tracking database (SQLite for simplicity)
        self.tracking_db_path = self.migrations_path / "migrations.db"
        self._init_tracking_database()
        
        self.migrations: Dict[str, Migration] = {}
        self.transformers: Dict[str, Callable] = {}
        
        # Register built-in transformers
        self._register_builtin_transformers()
    
    def _init_tracking_database(self):
        """Initialize migration tracking database."""
        with sqlite3.connect(self.tracking_db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS migrations (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    version TEXT NOT NULL,
                    description TEXT,
                    source_db_type TEXT NOT NULL,
                    target_db_type TEXT NOT NULL,
                    up_sql TEXT NOT NULL,
                    down_sql TEXT NOT NULL,
                    data_transformations TEXT,
                    dependencies TEXT,
                    status TEXT NOT NULL DEFAULT 'pending',
                    created_at TEXT NOT NULL,
                    executed_at TEXT,
                    execution_time_seconds REAL,
                    error_message TEXT
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS migration_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    migration_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    level TEXT NOT NULL,
                    message TEXT NOT NULL,
                    details TEXT,
                    FOREIGN KEY (migration_id) REFERENCES migrations (id)
                )
            """)
    
    def _register_builtin_transformers(self):
        """Register built-in data transformers."""
        
        def sqlite_to_postgresql_types(value: Any, source_type: str, target_type: str) -> Any:
            """Transform SQLite types to PostgreSQL types."""
            if source_type.upper() == 'TEXT' and target_type.upper() in ['JSON', 'JSONB']:
                try:
                    return json.loads(value) if isinstance(value, str) else value
                except (json.JSONDecodeError, TypeError):
                    return value
            return value
        
        def normalize_timestamps(value: Any, source_type: str, target_type: str) -> Any:
            """Normalize timestamp formats."""
            if 'TIMESTAMP' in target_type.upper() and isinstance(value, str):
                try:
                    # Try to parse and reformat timestamp
                    dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
                    return dt.isoformat()
                except ValueError:
                    return value
            return value
        
        def validate_email(value: Any, source_type: str, target_type: str) -> Any:
            """Validate email format."""
            if isinstance(value, str) and '@' in value:
                # Basic email validation
                if value.count('@') == 1 and '.' in value.split('@')[1]:
                    return value
                else:
                    return None  # Invalid email
            return value
        
        self.transformers.update({
            'sqlite_to_postgresql_types': sqlite_to_postgresql_types,
            'normalize_timestamps': normalize_timestamps,
            'validate_email': validate_email
        })
    
    async def create_migration(
        self,
        name: str,
        description: str,
        source_db_type: DatabaseType,
        target_db_type: DatabaseType,
        up_sql: str,
        down_sql: str = "",
        data_transformations: Optional[List[Dict[str, Any]]] = None,
        dependencies: Optional[List[str]] = None
    ) -> str:
        """
        Create a new migration.
        
        Args:
            name: Migration name
            description: Migration description
            source_db_type: Source database type
            target_db_type: Target database type
            up_sql: SQL to apply migration
            down_sql: SQL to rollback migration
            data_transformations: Data transformation rules
            dependencies: Migration dependencies
            
        Returns:
            Migration ID
        """
        
        # Generate migration ID and version
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        migration_id = f"{timestamp}_{name.lower().replace(' ', '_')}"
        version = datetime.now().strftime('%Y.%m.%d.%H%M%S')
        
        migration = Migration(
            id=migration_id,
            name=name,
            version=version,
            description=description,
            source_db_type=source_db_type,
            target_db_type=target_db_type,
            up_sql=up_sql,
            down_sql=down_sql,
            data_transformations=data_transformations or [],
            dependencies=dependencies or [],
            created_at=datetime.now().isoformat()
        )
        
        # Save migration to tracking database
        with sqlite3.connect(self.tracking_db_path) as conn:
            conn.execute("""
                INSERT INTO migrations (
                    id, name, version, description, source_db_type, target_db_type,
                    up_sql, down_sql, data_transformations, dependencies, status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                migration.id, migration.name, migration.version, migration.description,
                migration.source_db_type.value, migration.target_db_type.value,
                migration.up_sql, migration.down_sql,
                json.dumps(migration.data_transformations),
                json.dumps(migration.dependencies),
                migration.status.value, migration.created_at
            ))
        
        # Save migration file
        migration_file = self.migrations_path / f"{migration_id}.json"
        with open(migration_file, 'w') as f:
            json.dump(asdict(migration), f, indent=2, default=str)
        
        self.migrations[migration_id] = migration
        
        logger.info(f"Created migration: {migration_id}")
        return migration_id
    
    async def load_migrations(self) -> Dict[str, Migration]:
        """Load all migrations from files and database."""
        
        migrations = {}
        
        # Load from tracking database
        with sqlite3.connect(self.tracking_db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM migrations ORDER BY created_at")
            
            for row in cursor.fetchall():
                migration = Migration(
                    id=row['id'],
                    name=row['name'],
                    version=row['version'],
                    description=row['description'],
                    source_db_type=DatabaseType(row['source_db_type']),
                    target_db_type=DatabaseType(row['target_db_type']),
                    up_sql=row['up_sql'],
                    down_sql=row['down_sql'],
                    data_transformations=json.loads(row['data_transformations'] or '[]'),
                    dependencies=json.loads(row['dependencies'] or '[]'),
                    created_at=row['created_at'],
                    status=MigrationStatus(row['status']),
                    executed_at=row['executed_at'],
                    execution_time_seconds=row['execution_time_seconds'],
                    error_message=row['error_message']
                )
                migrations[migration.id] = migration
        
        self.migrations = migrations
        return migrations
    
    async def execute_migration(self, migration_id: str, source_db: str, target_db: str) -> Dict[str, Any]:
        """
        Execute a specific migration.
        
        Args:
            migration_id: Migration to execute
            source_db: Source database connection name
            target_db: Target database connection name
            
        Returns:
            Migration execution results
        """
        
        if migration_id not in self.migrations:
            raise ValueError(f"Migration {migration_id} not found")
        
        migration = self.migrations[migration_id]
        start_time = datetime.now()
        
        try:
            # Update status to running
            await self._update_migration_status(migration_id, MigrationStatus.RUNNING)
            await self._log_migration(migration_id, "INFO", "Starting migration execution")
            
            # Check dependencies
            for dep_id in migration.dependencies:
                dep_migration = self.migrations.get(dep_id)
                if not dep_migration or dep_migration.status != MigrationStatus.COMPLETED:
                    raise Exception(f"Dependency {dep_id} not completed")
            
            # Execute schema migration
            schema_result = await self._execute_schema_migration(migration, target_db)
            await self._log_migration(migration_id, "INFO", "Schema migration completed", schema_result)
            
            # Execute data migration if source database specified
            data_result = None
            if source_db and source_db != target_db:
                data_result = await self._execute_data_migration(migration, source_db, target_db)
                await self._log_migration(migration_id, "INFO", "Data migration completed", data_result)
            
            # Update status to completed
            execution_time = (datetime.now() - start_time).total_seconds()
            await self._update_migration_status(
                migration_id, 
                MigrationStatus.COMPLETED,
                execution_time=execution_time
            )
            
            result = {
                'success': True,
                'migration_id': migration_id,
                'execution_time_seconds': execution_time,
                'schema_result': schema_result,
                'data_result': data_result,
                'timestamp': datetime.now().isoformat()
            }
            
            await self._log_migration(migration_id, "INFO", "Migration completed successfully", result)
            logger.info(f"Migration {migration_id} completed successfully")
            
            return result
            
        except Exception as e:
            # Update status to failed
            execution_time = (datetime.now() - start_time).total_seconds()
            error_message = str(e)
            
            await self._update_migration_status(
                migration_id,
                MigrationStatus.FAILED,
                execution_time=execution_time,
                error_message=error_message
            )
            
            await self._log_migration(migration_id, "ERROR", f"Migration failed: {error_message}")
            logger.error(f"Migration {migration_id} failed: {e}")
            
            return {
                'success': False,
                'migration_id': migration_id,
                'execution_time_seconds': execution_time,
                'error': error_message,
                'timestamp': datetime.now().isoformat()
            }
    
    async def _execute_schema_migration(self, migration: Migration, target_db: str) -> Dict[str, Any]:
        """Execute schema migration."""
        
        if not migration.up_sql:
            return {'success': True, 'message': 'No schema changes required'}
        
        try:
            # Execute schema SQL
            result = await self.db_manager.execute_write(
                migration.up_sql,
                database=target_db
            )
            
            return {
                'success': result['success'],
                'affected_rows': result.get('affected_rows', 0),
                'execution_time_ms': result.get('execution_time_ms', 0)
            }
            
        except Exception as e:
            logger.error(f"Schema migration failed: {e}")
            raise
    
    async def _execute_data_migration(
        self,
        migration: Migration,
        source_db: str,
        target_db: str
    ) -> Dict[str, Any]:
        """Execute data migration with transformations."""
        
        try:
            migration_results = {}
            
            # Get list of tables from source database
            source_tables_result = await self.db_manager.list_tables(database=source_db)
            if not source_tables_result['success']:
                raise Exception(f"Failed to list source tables: {source_tables_result.get('error')}")
            
            source_tables = source_tables_result['tables']
            total_migrated = 0
            
            for table_name in source_tables:
                # Skip system tables
                if table_name.startswith('sqlite_') or table_name.startswith('_'):
                    continue
                
                table_result = await self._migrate_table_data(
                    table_name, migration, source_db, target_db
                )
                migration_results[table_name] = table_result
                total_migrated += table_result.get('migrated_records', 0)
            
            return {
                'success': True,
                'total_migrated_records': total_migrated,
                'tables': migration_results,
                'transformations_applied': len(migration.data_transformations)
            }
            
        except Exception as e:
            logger.error(f"Data migration failed: {e}")
            raise
    
    async def _migrate_table_data(
        self,
        table_name: str,
        migration: Migration,
        source_db: str,
        target_db: str
    ) -> Dict[str, Any]:
        """Migrate data for a specific table."""
        
        try:
            # Get source table schema
            source_schema_result = await self.db_manager.get_table_schema(table_name, database=source_db)
            if not source_schema_result['success']:
                return {'success': False, 'error': 'Failed to get source schema'}
            
            # Get all data from source table
            source_data_result = await self.db_manager.execute_query(
                f"SELECT * FROM {table_name}",
                database=source_db
            )
            
            if not source_data_result['success']:
                return {'success': False, 'error': 'Failed to fetch source data'}
            
            source_data = source_data_result['results']
            
            if not source_data:
                return {'success': True, 'migrated_records': 0, 'message': 'No data to migrate'}
            
            # Apply data transformations
            transformed_data = await self._apply_data_transformations(
                source_data, migration.data_transformations, migration.source_db_type, migration.target_db_type
            )
            
            # Insert data into target database
            if transformed_data:
                insert_result = await self.db_manager.insert_bulk(
                    table_name, transformed_data, database=target_db
                )
                
                if insert_result['success']:
                    return {
                        'success': True,
                        'migrated_records': insert_result['inserted_count'],
                        'source_records': len(source_data),
                        'transformations_applied': len(migration.data_transformations)
                    }
                else:
                    return {
                        'success': False,
                        'error': insert_result.get('error', 'Insert failed')
                    }
            else:
                return {
                    'success': True,
                    'migrated_records': 0,
                    'message': 'No data passed transformations'
                }
                
        except Exception as e:
            logger.error(f"Table data migration failed for {table_name}: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _apply_data_transformations(
        self,
        data: List[Dict[str, Any]],
        transformations: List[Dict[str, Any]],
        source_db_type: DatabaseType,
        target_db_type: DatabaseType
    ) -> List[Dict[str, Any]]:
        """Apply data transformations to migrated data."""
        
        if not transformations:
            return data
        
        transformed_data = []
        
        for record in data:
            transformed_record = record.copy()
            
            for transformation in transformations:
                transform_type = transformation.get('type')
                field_name = transformation.get('field')
                transformer_name = transformation.get('transformer')
                config = transformation.get('config', {})
                
                if transform_type == 'field_rename':
                    old_name = transformation.get('old_name')
                    new_name = transformation.get('new_name')
                    if old_name in transformed_record:
                        transformed_record[new_name] = transformed_record.pop(old_name)
                
                elif transform_type == 'field_transform' and transformer_name:
                    if transformer_name in self.transformers and field_name in transformed_record:
                        transformer = self.transformers[transformer_name]
                        source_type = config.get('source_type', 'TEXT')
                        target_type = config.get('target_type', 'TEXT')
                        
                        try:
                            transformed_record[field_name] = transformer(
                                transformed_record[field_name], source_type, target_type
                            )
                        except Exception as e:
                            logger.warning(f"Transformation failed for {field_name}: {e}")
                
                elif transform_type == 'field_remove':
                    if field_name in transformed_record:
                        del transformed_record[field_name]
                
                elif transform_type == 'field_add':
                    default_value = transformation.get('default_value')
                    transformed_record[field_name] = default_value
                
                elif transform_type == 'conditional':
                    condition = transformation.get('condition')
                    if condition and self._evaluate_condition(transformed_record, condition):
                        # Apply nested transformations
                        nested_transformations = transformation.get('transformations', [])
                        nested_data = await self._apply_data_transformations(
                            [transformed_record], nested_transformations, source_db_type, target_db_type
                        )
                        if nested_data:
                            transformed_record = nested_data[0]
            
            transformed_data.append(transformed_record)
        
        return transformed_data
    
    def _evaluate_condition(self, record: Dict[str, Any], condition: Dict[str, Any]) -> bool:
        """Evaluate a condition against a record."""
        
        field = condition.get('field')
        operator = condition.get('operator', 'equals')
        value = condition.get('value')
        
        if field not in record:
            return False
        
        record_value = record[field]
        
        if operator == 'equals':
            return record_value == value
        elif operator == 'not_equals':
            return record_value != value
        elif operator == 'contains':
            return value in str(record_value)
        elif operator == 'is_null':
            return record_value is None
        elif operator == 'is_not_null':
            return record_value is not None
        elif operator == 'greater_than':
            return record_value > value
        elif operator == 'less_than':
            return record_value < value
        
        return False
    
    async def rollback_migration(self, migration_id: str, target_db: str) -> Dict[str, Any]:
        """Rollback a migration."""
        
        if migration_id not in self.migrations:
            raise ValueError(f"Migration {migration_id} not found")
        
        migration = self.migrations[migration_id]
        start_time = datetime.now()
        
        try:
            await self._log_migration(migration_id, "INFO", "Starting migration rollback")
            
            if not migration.down_sql:
                return {
                    'success': False,
                    'error': 'No rollback SQL defined for this migration',
                    'migration_id': migration_id
                }
            
            # Execute rollback SQL
            result = await self.db_manager.execute_write(
                migration.down_sql,
                database=target_db
            )
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            if result['success']:
                # Update migration status
                await self._update_migration_status(migration_id, MigrationStatus.ROLLED_BACK)
                await self._log_migration(migration_id, "INFO", "Migration rollback completed successfully")
                
                return {
                    'success': True,
                    'migration_id': migration_id,
                    'execution_time_seconds': execution_time,
                    'affected_rows': result.get('affected_rows', 0),
                    'timestamp': datetime.now().isoformat()
                }
            else:
                await self._log_migration(migration_id, "ERROR", f"Rollback failed: {result.get('error')}")
                return {
                    'success': False,
                    'error': result.get('error'),
                    'migration_id': migration_id,
                    'execution_time_seconds': execution_time
                }
                
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            await self._log_migration(migration_id, "ERROR", f"Rollback failed: {str(e)}")
            
            return {
                'success': False,
                'error': str(e),
                'migration_id': migration_id,
                'execution_time_seconds': execution_time
            }
    
    async def _update_migration_status(
        self,
        migration_id: str,
        status: MigrationStatus,
        execution_time: Optional[float] = None,
        error_message: Optional[str] = None
    ):
        """Update migration status in tracking database."""
        
        with sqlite3.connect(self.tracking_db_path) as conn:
            if execution_time is not None:
                conn.execute("""
                    UPDATE migrations 
                    SET status = ?, executed_at = ?, execution_time_seconds = ?, error_message = ?
                    WHERE id = ?
                """, (
                    status.value, datetime.now().isoformat(), 
                    execution_time, error_message, migration_id
                ))
            else:
                conn.execute("""
                    UPDATE migrations 
                    SET status = ?
                    WHERE id = ?
                """, (status.value, migration_id))
        
        # Update in-memory migration
        if migration_id in self.migrations:
            self.migrations[migration_id].status = status
            if execution_time is not None:
                self.migrations[migration_id].executed_at = datetime.now().isoformat()
                self.migrations[migration_id].execution_time_seconds = execution_time
            if error_message:
                self.migrations[migration_id].error_message = error_message
    
    async def _log_migration(
        self,
        migration_id: str,
        level: str,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        """Log migration activity."""
        
        with sqlite3.connect(self.tracking_db_path) as conn:
            conn.execute("""
                INSERT INTO migration_logs (migration_id, timestamp, level, message, details)
                VALUES (?, ?, ?, ?, ?)
            """, (
                migration_id, datetime.now().isoformat(), level, message,
                json.dumps(details) if details else None
            ))
        
        # Also log to main logger
        if level == "ERROR":
            logger.error(f"Migration {migration_id}: {message}")
        elif level == "WARNING":
            logger.warning(f"Migration {migration_id}: {message}")
        else:
            logger.info(f"Migration {migration_id}: {message}")
    
    async def get_migration_status(self, migration_id: Optional[str] = None) -> Dict[str, Any]:
        """Get migration status and history."""
        
        await self.load_migrations()
        
        if migration_id:
            if migration_id not in self.migrations:
                return {'error': f'Migration {migration_id} not found'}
            
            migration = self.migrations[migration_id]
            
            # Get logs
            with sqlite3.connect(self.tracking_db_path) as conn:
                conn.row_factory = sqlite3.Row
                logs = conn.execute("""
                    SELECT timestamp, level, message, details
                    FROM migration_logs
                    WHERE migration_id = ?
                    ORDER BY timestamp DESC
                    LIMIT 100
                """, (migration_id,)).fetchall()
                
                migration_logs = [dict(log) for log in logs]
            
            return {
                'migration': asdict(migration),
                'logs': migration_logs
            }
        else:
            # Return all migrations summary
            summary = {
                'total_migrations': len(self.migrations),
                'completed': len([m for m in self.migrations.values() if m.status == MigrationStatus.COMPLETED]),
                'failed': len([m for m in self.migrations.values() if m.status == MigrationStatus.FAILED]),
                'pending': len([m for m in self.migrations.values() if m.status == MigrationStatus.PENDING]),
                'migrations': {
                    mid: {
                        'name': m.name,
                        'version': m.version,
                        'status': m.status.value,
                        'created_at': m.created_at,
                        'executed_at': m.executed_at,
                        'execution_time_seconds': m.execution_time_seconds
                    }
                    for mid, m in self.migrations.items()
                }
            }
            
            return summary
    
    async def create_sqlite_to_postgresql_migration(
        self,
        sqlite_db: str,
        postgresql_db: str,
        migration_name: str = "sqlite_to_postgresql"
    ) -> str:
        """Create a migration from SQLite to PostgreSQL."""
        
        # Analyze SQLite schema
        sqlite_schema_result = await self.db_manager.list_tables(database=sqlite_db)
        if not sqlite_schema_result['success']:
            raise Exception(f"Failed to analyze SQLite schema: {sqlite_schema_result.get('error')}")
        
        tables = sqlite_schema_result['tables']
        
        # Generate PostgreSQL schema
        up_sql_parts = []
        down_sql_parts = []
        
        for table_name in tables:
            if table_name.startswith('sqlite_'):
                continue
            
            # Get SQLite table schema
            schema_result = await self.db_manager.get_table_schema(table_name, database=sqlite_db)
            if not schema_result['success']:
                continue
            
            sqlite_schema = schema_result['schema']
            
            # Convert to PostgreSQL schema
            pg_columns = []
            for col_name, col_info in sqlite_schema.get('columns', {}).items():
                if col_name in ['id', 'created_at', 'updated_at']:
                    continue
                
                pg_type = self._convert_sqlite_to_postgresql_type(col_info.get('type', 'TEXT'))
                nullable = '' if col_info.get('nullable', True) else ' NOT NULL'
                
                pg_columns.append(f"    {col_name} {pg_type}{nullable}")
            
            # Add standard columns
            pg_columns.insert(0, "    id SERIAL PRIMARY KEY")
            pg_columns.append("    created_at TIMESTAMPTZ DEFAULT NOW()")
            pg_columns.append("    updated_at TIMESTAMPTZ DEFAULT NOW()")
            
            # Create table SQL
            create_table_sql = f"""
CREATE TABLE IF NOT EXISTS {table_name} (
{',\n'.join(pg_columns)}
);"""
            
            up_sql_parts.append(create_table_sql)
            down_sql_parts.append(f"DROP TABLE IF EXISTS {table_name};")
        
        # Data transformations
        data_transformations = [
            {
                'type': 'field_transform',
                'field': '*',
                'transformer': 'sqlite_to_postgresql_types',
                'config': {
                    'source_type': 'TEXT',
                    'target_type': 'JSONB'
                }
            },
            {
                'type': 'field_transform',
                'field': 'created_at',
                'transformer': 'normalize_timestamps',
                'config': {
                    'target_type': 'TIMESTAMPTZ'
                }
            },
            {
                'type': 'field_transform',
                'field': 'updated_at',
                'transformer': 'normalize_timestamps',
                'config': {
                    'target_type': 'TIMESTAMPTZ'
                }
            }
        ]
        
        migration_id = await self.create_migration(
            name=migration_name,
            description=f"Migrate from SQLite ({sqlite_db}) to PostgreSQL ({postgresql_db})",
            source_db_type=DatabaseType.POSTGRESQL,  # Note: assuming SQLite connector uses PostgreSQL type
            target_db_type=DatabaseType.POSTGRESQL,
            up_sql='\n\n'.join(up_sql_parts),
            down_sql='\n'.join(reversed(down_sql_parts)),
            data_transformations=data_transformations
        )
        
        return migration_id
    
    def _convert_sqlite_to_postgresql_type(self, sqlite_type: str) -> str:
        """Convert SQLite type to PostgreSQL type."""
        
        type_mapping = {
            'INTEGER': 'BIGINT',
            'TEXT': 'TEXT',
            'REAL': 'DOUBLE PRECISION',
            'BLOB': 'BYTEA',
            'NUMERIC': 'NUMERIC',
            'BOOLEAN': 'BOOLEAN',
            'TIMESTAMP': 'TIMESTAMPTZ',
            'DATETIME': 'TIMESTAMPTZ',
            'DATE': 'DATE',
            'TIME': 'TIME',
            'VARCHAR': 'VARCHAR',
            'CHAR': 'CHAR',
            'JSON': 'JSONB'
        }
        
        return type_mapping.get(sqlite_type.upper(), 'TEXT')