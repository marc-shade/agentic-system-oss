"""
Database Manager for orchestrating multiple database connections and operations.

Provides:
- Multi-database connection management
- Unified query interface across different database types
- Connection pooling and health monitoring
- Load balancing and failover
- Performance optimization
"""

import asyncio
import json
from typing import Any, Dict, List, Optional, Union, Type
from datetime import datetime, timedelta
from loguru import logger
from enum import Enum

from .base import DatabaseConnector, ConnectionManager, connection_manager
from .connectors import (
    PostgreSQLConnector, MySQLConnector, MongoDBConnector, RedisConnector,
    BigQueryConnector, SnowflakeConnector, RedshiftConnector
)


class DatabaseType(Enum):
    """Supported database types."""
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    MONGODB = "mongodb"
    REDIS = "redis"
    BIGQUERY = "bigquery"
    SNOWFLAKE = "snowflake"
    REDSHIFT = "redshift"


class DatabaseRole(Enum):
    """Database roles in multi-database architecture."""
    PRIMARY = "primary"          # Main operational database
    REPLICA = "replica"          # Read replica
    CACHE = "cache"             # Caching layer
    ANALYTICS = "analytics"      # Analytics/data warehouse
    ARCHIVE = "archive"         # Long-term storage


class DatabaseManager:
    """Central database manager for multi-database operations."""
    
    def __init__(self):
        """Initialize database manager."""
        self.connectors: Dict[str, DatabaseConnector] = {}
        self.configurations: Dict[str, Dict[str, Any]] = {}
        self.roles: Dict[DatabaseRole, List[str]] = {}
        self.health_status: Dict[str, Dict[str, Any]] = {}
        self._connection_manager = connection_manager
        
        # Performance metrics
        self.query_metrics: Dict[str, List[Dict[str, Any]]] = {}
        self.error_counts: Dict[str, int] = {}
        
        # Database type mapping
        self.connector_classes: Dict[DatabaseType, Type[DatabaseConnector]] = {
            DatabaseType.POSTGRESQL: PostgreSQLConnector,
            DatabaseType.MYSQL: MySQLConnector,
            DatabaseType.MONGODB: MongoDBConnector,
            DatabaseType.REDIS: RedisConnector,
            DatabaseType.BIGQUERY: BigQueryConnector,
            DatabaseType.SNOWFLAKE: SnowflakeConnector,
            DatabaseType.REDSHIFT: RedshiftConnector
        }
    
    async def add_database(
        self,
        name: str,
        db_type: DatabaseType,
        config: Dict[str, Any],
        role: DatabaseRole = DatabaseRole.PRIMARY,
        auto_connect: bool = True
    ) -> bool:
        """
        Add database connection to manager.
        
        Args:
            name: Unique identifier for this database connection
            db_type: Type of database
            config: Database connection configuration
            role: Role this database plays in the architecture
            auto_connect: Whether to connect immediately
            
        Returns:
            True if successfully added and connected (if auto_connect)
        """
        try:
            # Get connector class
            connector_class = self.connector_classes[db_type]
            
            # Create connector instance
            connector = connector_class(config)
            
            # Store configuration and connector
            self.configurations[name] = {
                'type': db_type,
                'config': config,
                'role': role,
                'added_at': datetime.now().isoformat()
            }
            
            self.connectors[name] = connector
            self._connection_manager.register_connector(name, connector)
            
            # Add to role mapping
            if role not in self.roles:
                self.roles[role] = []
            self.roles[role].append(name)
            
            # Initialize metrics
            self.query_metrics[name] = []
            self.error_counts[name] = 0
            
            # Connect if requested
            if auto_connect:
                success = await connector.connect()
                if not success:
                    logger.error(f"Failed to connect to {name}")
                    return False
            
            logger.info(f"Added {db_type.value} database: {name} (role: {role.value})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add database {name}: {e}")
            return False
    
    async def remove_database(self, name: str) -> bool:
        """Remove database connection."""
        try:
            if name in self.connectors:
                # Disconnect
                await self.connectors[name].disconnect()
                
                # Remove from role mapping
                for role, databases in self.roles.items():
                    if name in databases:
                        databases.remove(name)
                
                # Clean up
                del self.connectors[name]
                del self.configurations[name]
                del self.query_metrics[name]
                del self.error_counts[name]
                
                logger.info(f"Removed database: {name}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to remove database {name}: {e}")
            return False
    
    async def connect_all(self) -> Dict[str, bool]:
        """Connect all registered databases."""
        results = {}
        
        for name, connector in self.connectors.items():
            try:
                success = await connector.connect()
                results[name] = success
                
                if success:
                    logger.info(f"Connected to {name}")
                else:
                    logger.error(f"Failed to connect to {name}")
                    self.error_counts[name] += 1
                    
            except Exception as e:
                logger.error(f"Connection error for {name}: {e}")
                results[name] = False
                self.error_counts[name] += 1
        
        return results
    
    async def disconnect_all(self):
        """Disconnect all databases."""
        for name, connector in self.connectors.items():
            try:
                await connector.disconnect()
                logger.info(f"Disconnected from {name}")
            except Exception as e:
                logger.error(f"Disconnect error for {name}: {e}")
    
    async def execute_query(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
        database: Optional[str] = None,
        role: Optional[DatabaseRole] = None
    ) -> Dict[str, Any]:
        """
        Execute query with intelligent database selection.
        
        Args:
            query: SQL or database-specific query
            parameters: Query parameters
            database: Specific database name (optional)
            role: Database role to use (optional)
            
        Returns:
            Query results with metadata
        """
        start_time = datetime.now()
        
        try:
            # Select database
            db_name = await self._select_database(database, role, 'read')
            if not db_name:
                raise ValueError("No suitable database found")
            
            connector = self.connectors[db_name]
            
            # Execute query
            results = await connector.execute_query(query, parameters)
            
            # Record metrics
            execution_time = (datetime.now() - start_time).total_seconds()
            self._record_query_metric(db_name, 'query', execution_time, len(results), True)
            
            return {
                'success': True,
                'database': db_name,
                'results': results,
                'execution_time_ms': execution_time * 1000,
                'row_count': len(results),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            self.error_counts[db_name] += 1
            self._record_query_metric(db_name, 'query', execution_time, 0, False)
            
            logger.error(f"Query execution failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'execution_time_ms': execution_time * 1000,
                'timestamp': datetime.now().isoformat()
            }
    
    async def execute_write(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
        database: Optional[str] = None,
        role: Optional[DatabaseRole] = None
    ) -> Dict[str, Any]:
        """
        Execute write operation with database selection.
        
        Args:
            query: SQL or database-specific write operation
            parameters: Query parameters
            database: Specific database name (optional)
            role: Database role to use (optional)
            
        Returns:
            Write operation results
        """
        start_time = datetime.now()
        
        try:
            # Select database (prefer PRIMARY for writes)
            db_name = await self._select_database(database, role or DatabaseRole.PRIMARY, 'write')
            if not db_name:
                raise ValueError("No suitable database found for write operation")
            
            connector = self.connectors[db_name]
            
            # Execute write operation
            affected_rows = await connector.execute_write(query, parameters)
            
            # Record metrics
            execution_time = (datetime.now() - start_time).total_seconds()
            self._record_query_metric(db_name, 'write', execution_time, affected_rows, True)
            
            return {
                'success': True,
                'database': db_name,
                'affected_rows': affected_rows,
                'execution_time_ms': execution_time * 1000,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            if 'db_name' in locals():
                self.error_counts[db_name] += 1
                self._record_query_metric(db_name, 'write', execution_time, 0, False)
            
            logger.error(f"Write operation failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'execution_time_ms': execution_time * 1000,
                'timestamp': datetime.now().isoformat()
            }
    
    async def insert_bulk(
        self,
        table_name: str,
        data: List[Dict[str, Any]],
        database: Optional[str] = None,
        role: Optional[DatabaseRole] = None
    ) -> Dict[str, Any]:
        """
        Bulk insert operation with intelligent database selection.
        
        Args:
            table_name: Target table name
            data: List of records to insert
            database: Specific database name (optional)
            role: Database role to use (optional)
            
        Returns:
            Bulk insert results
        """
        start_time = datetime.now()
        
        try:
            # Select database
            db_name = await self._select_database(database, role or DatabaseRole.PRIMARY, 'write')
            if not db_name:
                raise ValueError("No suitable database found for bulk insert")
            
            connector = self.connectors[db_name]
            
            # Execute bulk insert
            inserted_count = await connector.insert_bulk(table_name, data)
            
            # Record metrics
            execution_time = (datetime.now() - start_time).total_seconds()
            self._record_query_metric(db_name, 'bulk_insert', execution_time, inserted_count, True)
            
            return {
                'success': True,
                'database': db_name,
                'table_name': table_name,
                'inserted_count': inserted_count,
                'execution_time_ms': execution_time * 1000,
                'records_per_second': inserted_count / execution_time if execution_time > 0 else 0,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            if 'db_name' in locals():
                self.error_counts[db_name] += 1
                self._record_query_metric(db_name, 'bulk_insert', execution_time, 0, False)
            
            logger.error(f"Bulk insert failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'execution_time_ms': execution_time * 1000,
                'timestamp': datetime.now().isoformat()
            }
    
    async def create_table(
        self,
        table_name: str,
        schema: Dict[str, Any],
        database: Optional[str] = None,
        role: Optional[DatabaseRole] = None
    ) -> Dict[str, Any]:
        """Create table across specified databases."""
        results = {}
        
        # Determine target databases
        if database:
            target_databases = [database]
        elif role:
            target_databases = self.roles.get(role, [])
        else:
            # Create in all PRIMARY databases by default
            target_databases = self.roles.get(DatabaseRole.PRIMARY, [])
        
        for db_name in target_databases:
            try:
                connector = self.connectors[db_name]
                success = await connector.create_table(table_name, schema)
                results[db_name] = {'success': success}
                
            except Exception as e:
                logger.error(f"Table creation failed on {db_name}: {e}")
                results[db_name] = {'success': False, 'error': str(e)}
                self.error_counts[db_name] += 1
        
        return {
            'table_name': table_name,
            'results': results,
            'overall_success': all(r['success'] for r in results.values()),
            'timestamp': datetime.now().isoformat()
        }
    
    async def get_table_schema(
        self,
        table_name: str,
        database: Optional[str] = None,
        role: Optional[DatabaseRole] = None
    ) -> Dict[str, Any]:
        """Get table schema from specified database."""
        try:
            db_name = await self._select_database(database, role, 'read')
            if not db_name:
                raise ValueError("No suitable database found")
            
            connector = self.connectors[db_name]
            schema = await connector.get_table_schema(table_name)
            
            return {
                'success': True,
                'database': db_name,
                'table_name': table_name,
                'schema': schema,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get schema for {table_name}: {e}")
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    async def list_tables(
        self,
        database: Optional[str] = None,
        role: Optional[DatabaseRole] = None
    ) -> Dict[str, Any]:
        """List tables from specified database."""
        try:
            db_name = await self._select_database(database, role, 'read')
            if not db_name:
                raise ValueError("No suitable database found")
            
            connector = self.connectors[db_name]
            tables = await connector.list_tables()
            
            return {
                'success': True,
                'database': db_name,
                'tables': tables,
                'table_count': len(tables),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to list tables: {e}")
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    async def _select_database(
        self,
        database: Optional[str],
        role: Optional[DatabaseRole],
        operation_type: str
    ) -> Optional[str]:
        """
        Intelligent database selection based on criteria.
        
        Args:
            database: Specific database name
            role: Database role preference
            operation_type: Type of operation (read/write)
            
        Returns:
            Selected database name or None
        """
        # Direct database specification
        if database:
            if database in self.connectors and self.connectors[database].is_connected:
                return database
            return None
        
        # Role-based selection
        if role:
            candidates = self.roles.get(role, [])
        else:
            # Default selection logic
            if operation_type == 'write':
                candidates = self.roles.get(DatabaseRole.PRIMARY, [])
            else:
                # For reads, prefer replicas, then primary
                candidates = (
                    self.roles.get(DatabaseRole.REPLICA, []) +
                    self.roles.get(DatabaseRole.PRIMARY, [])
                )
        
        # Filter connected databases and select best one
        connected_candidates = [
            db for db in candidates
            if db in self.connectors and self.connectors[db].is_connected
        ]
        
        if not connected_candidates:
            return None
        
        # Simple load balancing - select database with lowest error count
        return min(connected_candidates, key=lambda db: self.error_counts.get(db, 0))
    
    def _record_query_metric(
        self,
        database: str,
        operation_type: str,
        execution_time: float,
        result_count: int,
        success: bool
    ):
        """Record query performance metrics."""
        metric = {
            'timestamp': datetime.now().isoformat(),
            'operation_type': operation_type,
            'execution_time': execution_time,
            'result_count': result_count,
            'success': success
        }
        
        self.query_metrics[database].append(metric)
        
        # Keep only recent metrics (last 1000)
        if len(self.query_metrics[database]) > 1000:
            self.query_metrics[database] = self.query_metrics[database][-1000:]
    
    async def health_check_all(self) -> Dict[str, Any]:
        """Comprehensive health check for all databases."""
        health_results = {}
        overall_healthy = True
        
        for name, connector in self.connectors.items():
            try:
                start_time = datetime.now()
                health_status = await connector.health_check()
                check_time = (datetime.now() - start_time).total_seconds()
                
                # Add manager-specific metrics
                recent_metrics = self.query_metrics[name][-100:]  # Last 100 queries
                
                if recent_metrics:
                    avg_response_time = sum(m['execution_time'] for m in recent_metrics) / len(recent_metrics)
                    success_rate = sum(1 for m in recent_metrics if m['success']) / len(recent_metrics)
                else:
                    avg_response_time = 0
                    success_rate = 1.0
                
                health_results[name] = {
                    **health_status,
                    'manager_metrics': {
                        'avg_response_time_ms': avg_response_time * 1000,
                        'success_rate': success_rate,
                        'error_count': self.error_counts[name],
                        'recent_query_count': len(recent_metrics),
                        'health_check_time_ms': check_time * 1000
                    },
                    'configuration': {
                        'type': self.configurations[name]['type'].value,
                        'role': next((role.value for role, dbs in self.roles.items() if name in dbs), 'unknown'),
                        'added_at': self.configurations[name]['added_at']
                    }
                }
                
                if health_status.get('status') != 'healthy':
                    overall_healthy = False
                    
            except Exception as e:
                logger.error(f"Health check failed for {name}: {e}")
                health_results[name] = {
                    'status': 'unhealthy',
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                }
                overall_healthy = False
                self.error_counts[name] += 1
        
        # Store health status for monitoring
        self.health_status = health_results
        
        return {
            'overall_status': 'healthy' if overall_healthy else 'degraded',
            'database_count': len(self.connectors),
            'healthy_databases': sum(1 for r in health_results.values() if r.get('status') == 'healthy'),
            'databases': health_results,
            'roles_configured': {role.value: len(dbs) for role, dbs in self.roles.items()},
            'timestamp': datetime.now().isoformat()
        }
    
    async def get_performance_metrics(self, database: Optional[str] = None) -> Dict[str, Any]:
        """Get performance metrics for databases."""
        if database and database in self.query_metrics:
            metrics = {database: self.query_metrics[database]}
        else:
            metrics = self.query_metrics
        
        performance_summary = {}
        
        for db_name, db_metrics in metrics.items():
            if not db_metrics:
                performance_summary[db_name] = {
                    'query_count': 0,
                    'avg_response_time_ms': 0,
                    'success_rate': 1.0,
                    'error_count': self.error_counts[db_name]
                }
                continue
            
            # Calculate metrics for last hour
            one_hour_ago = datetime.now() - timedelta(hours=1)
            recent_metrics = [
                m for m in db_metrics
                if datetime.fromisoformat(m['timestamp']) > one_hour_ago
            ]
            
            if recent_metrics:
                avg_time = sum(m['execution_time'] for m in recent_metrics) / len(recent_metrics)
                success_count = sum(1 for m in recent_metrics if m['success'])
                success_rate = success_count / len(recent_metrics)
                
                # Operation breakdown
                operations = {}
                for metric in recent_metrics:
                    op_type = metric['operation_type']
                    if op_type not in operations:
                        operations[op_type] = {'count': 0, 'total_time': 0, 'successes': 0}
                    
                    operations[op_type]['count'] += 1
                    operations[op_type]['total_time'] += metric['execution_time']
                    if metric['success']:
                        operations[op_type]['successes'] += 1
                
                for op_type in operations:
                    op = operations[op_type]
                    op['avg_time_ms'] = (op['total_time'] / op['count']) * 1000
                    op['success_rate'] = op['successes'] / op['count']
                
                performance_summary[db_name] = {
                    'query_count': len(recent_metrics),
                    'avg_response_time_ms': avg_time * 1000,
                    'success_rate': success_rate,
                    'error_count': self.error_counts[db_name],
                    'operations': operations,
                    'database_type': self.configurations[db_name]['type'].value,
                    'role': next((role.value for role, dbs in self.roles.items() if db_name in dbs), 'unknown')
                }
            else:
                performance_summary[db_name] = {
                    'query_count': 0,
                    'avg_response_time_ms': 0,
                    'success_rate': 1.0,
                    'error_count': self.error_counts[db_name]
                }
        
        return {
            'time_period': 'last_hour',
            'databases': performance_summary,
            'generated_at': datetime.now().isoformat()
        }
    
    async def optimize_connections(self) -> Dict[str, Any]:
        """Optimize database connections based on performance metrics."""
        optimization_results = {}
        
        for db_name, connector in self.connectors.items():
            try:
                # Get recent performance metrics
                recent_metrics = self.query_metrics[db_name][-100:]
                
                if not recent_metrics:
                    continue
                
                # Calculate performance indicators
                avg_response_time = sum(m['execution_time'] for m in recent_metrics) / len(recent_metrics)
                error_rate = (len([m for m in recent_metrics if not m['success']]) / len(recent_metrics))
                
                optimizations = []
                
                # High response time optimization
                if avg_response_time > 5.0:  # 5 seconds
                    optimizations.append({
                        'type': 'high_response_time',
                        'description': f'Average response time is {avg_response_time:.2f}s',
                        'recommendation': 'Consider connection pooling optimization or query optimization'
                    })
                
                # High error rate optimization
                if error_rate > 0.1:  # 10% error rate
                    optimizations.append({
                        'type': 'high_error_rate',
                        'description': f'Error rate is {error_rate:.2%}',
                        'recommendation': 'Check database health and connection stability'
                    })
                
                # Database-specific optimizations
                if hasattr(connector, 'optimize_table'):
                    # This would be implemented for specific database types
                    pass
                
                optimization_results[db_name] = {
                    'performance_score': max(0, 100 - (avg_response_time * 10) - (error_rate * 100)),
                    'optimizations': optimizations,
                    'metrics': {
                        'avg_response_time': avg_response_time,
                        'error_rate': error_rate,
                        'recent_query_count': len(recent_metrics)
                    }
                }
                
            except Exception as e:
                logger.error(f"Optimization analysis failed for {db_name}: {e}")
                optimization_results[db_name] = {
                    'error': str(e)
                }
        
        return {
            'optimization_results': optimization_results,
            'timestamp': datetime.now().isoformat()
        }
    
    def get_database_info(self) -> Dict[str, Any]:
        """Get comprehensive information about managed databases."""
        return {
            'total_databases': len(self.connectors),
            'connected_databases': sum(1 for c in self.connectors.values() if c.is_connected),
            'database_types': {
                db_type.value: sum(
                    1 for config in self.configurations.values()
                    if config['type'] == db_type
                )
                for db_type in DatabaseType
            },
            'role_distribution': {
                role.value: len(databases)
                for role, databases in self.roles.items()
            },
            'configurations': {
                name: {
                    'type': config['type'].value,
                    'role': next((role.value for role, dbs in self.roles.items() if name in dbs), 'unknown'),
                    'connected': self.connectors[name].is_connected,
                    'added_at': config['added_at']
                }
                for name, config in self.configurations.items()
            },
            'health_status': self.health_status,
            'timestamp': datetime.now().isoformat()
        }


# Global database manager instance
database_manager = DatabaseManager()