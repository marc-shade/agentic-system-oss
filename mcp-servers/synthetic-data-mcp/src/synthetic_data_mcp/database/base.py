"""
Base database connector interface and common functionality.

Provides abstract base classes and shared utilities for all database connectors.
"""

import asyncio
from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional, Union, AsyncGenerator
from datetime import datetime
from loguru import logger
import json


class DatabaseConnector(ABC):
    """Abstract base class for all database connectors."""
    
    def __init__(self, connection_config: Dict[str, Any]):
        """
        Initialize database connector.
        
        Args:
            connection_config: Database connection parameters
        """
        self.config = connection_config
        self.connection_pool = None
        self._connected = False
        
    @abstractmethod
    async def connect(self) -> bool:
        """
        Establish database connection.
        
        Returns:
            True if connection successful, False otherwise
        """
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Close database connection and cleanup resources."""
        pass
    
    @abstractmethod
    async def execute_query(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Execute a database query.
        
        Args:
            query: SQL query or database-specific query string
            parameters: Query parameters
            
        Returns:
            Query results as list of dictionaries
        """
        pass
    
    @abstractmethod
    async def execute_write(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> int:
        """
        Execute a write operation (INSERT, UPDATE, DELETE).
        
        Args:
            query: SQL/database query
            parameters: Query parameters
            
        Returns:
            Number of affected rows
        """
        pass
    
    @abstractmethod
    async def create_table(self, table_name: str, schema: Dict[str, Any]) -> bool:
        """
        Create a table with given schema.
        
        Args:
            table_name: Name of the table to create
            schema: Table schema definition
            
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    async def insert_bulk(self, table_name: str, data: List[Dict[str, Any]]) -> int:
        """
        Insert multiple records efficiently.
        
        Args:
            table_name: Target table name
            data: List of records to insert
            
        Returns:
            Number of records inserted
        """
        pass
    
    @abstractmethod
    async def get_table_schema(self, table_name: str) -> Dict[str, Any]:
        """
        Get table schema information.
        
        Args:
            table_name: Name of the table
            
        Returns:
            Schema information including columns, types, constraints
        """
        pass
    
    @abstractmethod
    async def list_tables(self) -> List[str]:
        """
        List all tables in the database.
        
        Returns:
            List of table names
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform database health check.
        
        Returns:
            Health status information
        """
        pass
    
    @property
    def is_connected(self) -> bool:
        """Check if database is connected."""
        return self._connected
    
    @property
    def database_type(self) -> str:
        """Get database type identifier."""
        return self.__class__.__name__.replace('Connector', '').lower()


class RelationalDatabaseConnector(DatabaseConnector):
    """Base class for relational databases (PostgreSQL, MySQL)."""
    
    @abstractmethod
    async def begin_transaction(self):
        """Begin database transaction."""
        pass
    
    @abstractmethod
    async def commit_transaction(self):
        """Commit current transaction."""
        pass
    
    @abstractmethod
    async def rollback_transaction(self):
        """Rollback current transaction."""
        pass
    
    @asynccontextmanager
    async def transaction(self):
        """Transaction context manager."""
        await self.begin_transaction()
        try:
            yield
            await self.commit_transaction()
        except Exception:
            await self.rollback_transaction()
            raise
    
    async def execute_migration(self, migration_sql: str) -> bool:
        """
        Execute database migration.
        
        Args:
            migration_sql: SQL migration script
            
        Returns:
            True if successful, False otherwise
        """
        try:
            async with self.transaction():
                await self.execute_write(migration_sql)
            return True
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            return False
    
    async def create_index(self, table_name: str, column_name: str, index_type: str = "btree") -> bool:
        """
        Create database index.
        
        Args:
            table_name: Target table
            column_name: Column to index
            index_type: Type of index (btree, gin, gist, hash)
            
        Returns:
            True if successful
        """
        index_name = f"idx_{table_name}_{column_name}"
        query = f"CREATE INDEX IF NOT EXISTS {index_name} ON {table_name} USING {index_type} ({column_name})"
        
        try:
            await self.execute_write(query)
            logger.info(f"Created index: {index_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to create index {index_name}: {e}")
            return False


class NoSQLDatabaseConnector(DatabaseConnector):
    """Base class for NoSQL databases (MongoDB, Redis)."""
    
    @abstractmethod
    async def create_collection(self, collection_name: str, schema: Optional[Dict[str, Any]] = None) -> bool:
        """
        Create a collection/keyspace.
        
        Args:
            collection_name: Name of collection to create
            schema: Optional schema definition
            
        Returns:
            True if successful
        """
        pass
    
    @abstractmethod
    async def insert_document(self, collection_name: str, document: Dict[str, Any]) -> str:
        """
        Insert a single document.
        
        Args:
            collection_name: Target collection
            document: Document to insert
            
        Returns:
            Document ID
        """
        pass
    
    @abstractmethod
    async def find_documents(self, collection_name: str, query: Dict[str, Any], limit: int = 100) -> List[Dict[str, Any]]:
        """
        Find documents matching query.
        
        Args:
            collection_name: Collection to search
            query: Query criteria
            limit: Maximum results to return
            
        Returns:
            Matching documents
        """
        pass


class CloudDatabaseConnector(DatabaseConnector):
    """Base class for cloud database services."""
    
    def __init__(self, connection_config: Dict[str, Any]):
        super().__init__(connection_config)
        self.client = None
        self._setup_authentication()
    
    @abstractmethod
    def _setup_authentication(self):
        """Setup cloud provider authentication."""
        pass
    
    @abstractmethod
    async def create_dataset(self, dataset_name: str, location: Optional[str] = None) -> bool:
        """
        Create a dataset/database in cloud service.
        
        Args:
            dataset_name: Name of dataset to create
            location: Geographic location for data
            
        Returns:
            True if successful
        """
        pass
    
    @abstractmethod
    async def upload_data(self, table_name: str, data: List[Dict[str, Any]], dataset_name: Optional[str] = None) -> int:
        """
        Upload data to cloud table.
        
        Args:
            table_name: Target table
            data: Data to upload
            dataset_name: Optional dataset name
            
        Returns:
            Number of records uploaded
        """
        pass


class ConnectionManager:
    """Manages database connection lifecycle and pooling."""
    
    def __init__(self):
        self.connections: Dict[str, DatabaseConnector] = {}
        self.connection_stats = {}
    
    def register_connector(self, name: str, connector: DatabaseConnector):
        """Register a database connector."""
        self.connections[name] = connector
        self.connection_stats[name] = {
            'created_at': datetime.now(),
            'query_count': 0,
            'error_count': 0,
            'last_used': None
        }
        logger.info(f"Registered database connector: {name}")
    
    def get_connector(self, name: str) -> DatabaseConnector:
        """Get database connector by name."""
        if name not in self.connections:
            raise ValueError(f"Database connector '{name}' not found")
        
        self.connection_stats[name]['last_used'] = datetime.now()
        return self.connections[name]
    
    async def connect_all(self) -> Dict[str, bool]:
        """Connect all registered databases."""
        results = {}
        
        for name, connector in self.connections.items():
            try:
                result = await connector.connect()
                results[name] = result
                logger.info(f"Connected to {name}: {result}")
            except Exception as e:
                results[name] = False
                self.connection_stats[name]['error_count'] += 1
                logger.error(f"Failed to connect to {name}: {e}")
        
        return results
    
    async def disconnect_all(self):
        """Disconnect all database connections."""
        for name, connector in self.connections.items():
            try:
                await connector.disconnect()
                logger.info(f"Disconnected from {name}")
            except Exception as e:
                logger.error(f"Error disconnecting from {name}: {e}")
    
    async def health_check_all(self) -> Dict[str, Dict[str, Any]]:
        """Perform health check on all connections."""
        results = {}
        
        for name, connector in self.connections.items():
            try:
                health_status = await connector.health_check()
                results[name] = {
                    'status': 'healthy',
                    'details': health_status,
                    'stats': self.connection_stats[name]
                }
            except Exception as e:
                results[name] = {
                    'status': 'unhealthy',
                    'error': str(e),
                    'stats': self.connection_stats[name]
                }
        
        return results
    
    def get_connection_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get connection statistics."""
        return self.connection_stats.copy()


# Global connection manager instance
connection_manager = ConnectionManager()