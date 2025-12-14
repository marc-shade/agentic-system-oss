"""
MongoDB connector for document storage and NoSQL operations.

Supports:
- Connection pooling with motor
- MongoDB aggregation pipelines
- GridFS for large files
- Change streams
- Transactions (MongoDB 4.0+)
- Schema validation
"""

import asyncio
import json
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, timedelta
from bson import ObjectId
from loguru import logger

try:
    import motor.motor_asyncio
    from pymongo import IndexModel, ASCENDING, DESCENDING, TEXT, GEO2D
    from pymongo.errors import DuplicateKeyError, OperationFailure
    from bson import json_util
except ImportError:
    motor = None
    IndexModel = None
    ASCENDING = DESCENDING = TEXT = GEO2D = None
    DuplicateKeyError = OperationFailure = None
    json_util = None
    logger.warning("motor (MongoDB driver) not installed - MongoDB connector disabled")

from ..base import NoSQLDatabaseConnector


class MongoDBConnector(NoSQLDatabaseConnector):
    """High-performance MongoDB connector with advanced features."""
    
    def __init__(self, connection_config: Dict[str, Any]):
        """
        Initialize MongoDB connector.
        
        Args:
            connection_config: MongoDB connection parameters
                - host: MongoDB host (default: localhost)
                - port: MongoDB port (default: 27017)
                - database: Database name
                - username: Username (optional)
                - password: Password (optional)
                - auth_source: Authentication database (default: admin)
                - replica_set: Replica set name (optional)
                - ssl: Use SSL (default: False)
                - max_pool_size: Maximum connections (default: 100)
                - min_pool_size: Minimum connections (default: 10)
                - max_idle_time_ms: Max idle time in ms (default: 30000)
        """
        if motor is None:
            raise ImportError("motor is required for MongoDB connector. Install with: pip install motor")
            
        super().__init__(connection_config)
        
        # Set defaults
        self.config.setdefault('host', 'localhost')
        self.config.setdefault('port', 27017)
        self.config.setdefault('auth_source', 'admin')
        self.config.setdefault('ssl', False)
        self.config.setdefault('max_pool_size', 100)
        self.config.setdefault('min_pool_size', 10)
        self.config.setdefault('max_idle_time_ms', 30000)
        
        self.client = None
        self.database = None
    
    async def connect(self) -> bool:
        """Establish MongoDB connection."""
        try:
            # Build connection URI
            if self.config.get('username') and self.config.get('password'):
                auth_string = f"{self.config['username']}:{self.config['password']}@"
            else:
                auth_string = ""
            
            uri_parts = [
                f"mongodb://{auth_string}{self.config['host']}:{self.config['port']}/{self.config['database']}"
            ]
            
            # Add connection options
            options = []
            if self.config.get('replica_set'):
                options.append(f"replicaSet={self.config['replica_set']}")
            if self.config.get('auth_source'):
                options.append(f"authSource={self.config['auth_source']}")
            options.append(f"maxPoolSize={self.config['max_pool_size']}")
            options.append(f"minPoolSize={self.config['min_pool_size']}")
            options.append(f"maxIdleTimeMS={self.config['max_idle_time_ms']}")
            if self.config['ssl']:
                options.append("ssl=true")
            
            if options:
                uri_parts.append("?" + "&".join(options))
            
            connection_uri = "".join(uri_parts)
            
            # Create client
            self.client = motor.motor_asyncio.AsyncIOMotorClient(connection_uri)
            self.database = self.client[self.config['database']]
            
            # Test connection
            await self.client.admin.command('ping')
            
            # Get server info
            server_info = await self.client.server_info()
            logger.info(f"Connected to MongoDB {server_info['version']}")
            
            self._connected = True
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            self._connected = False
            return False
    
    async def disconnect(self) -> None:
        """Close MongoDB connection."""
        if self.client:
            self.client.close()
            self.client = None
            self.database = None
        self._connected = False
        logger.info("Disconnected from MongoDB")
    
    async def execute_query(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Execute MongoDB query (find operation)."""
        # MongoDB doesn't use SQL queries, so we interpret the query parameter as collection name
        # and parameters as the query document
        
        if not self.database:
            raise RuntimeError("Not connected to database")
        
        try:
            collection_name = query
            filter_doc = parameters or {}
            
            collection = self.database[collection_name]
            cursor = collection.find(filter_doc)
            
            results = []
            async for document in cursor:
                # Convert ObjectId to string for JSON serialization
                document['_id'] = str(document['_id'])
                results.append(document)
            
            return results
            
        except Exception as e:
            logger.error(f"MongoDB query failed: {e}")
            logger.error(f"Collection: {query}")
            logger.error(f"Filter: {parameters}")
            raise
    
    async def execute_write(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> int:
        """Execute MongoDB write operation."""
        # For MongoDB, we use query to specify operation type and collection
        # Format: "operation:collection_name"
        
        if not self.database:
            raise RuntimeError("Not connected to database")
        
        try:
            operation, collection_name = query.split(':', 1)
            collection = self.database[collection_name]
            
            if operation == 'insert_one':
                result = await collection.insert_one(parameters)
                return 1 if result.inserted_id else 0
            
            elif operation == 'insert_many':
                documents = parameters.get('documents', [])
                result = await collection.insert_many(documents)
                return len(result.inserted_ids)
            
            elif operation == 'update_one':
                filter_doc = parameters.get('filter', {})
                update_doc = parameters.get('update', {})
                result = await collection.update_one(filter_doc, update_doc)
                return result.modified_count
            
            elif operation == 'update_many':
                filter_doc = parameters.get('filter', {})
                update_doc = parameters.get('update', {})
                result = await collection.update_many(filter_doc, update_doc)
                return result.modified_count
            
            elif operation == 'delete_one':
                filter_doc = parameters.get('filter', {})
                result = await collection.delete_one(filter_doc)
                return result.deleted_count
            
            elif operation == 'delete_many':
                filter_doc = parameters.get('filter', {})
                result = await collection.delete_many(filter_doc)
                return result.deleted_count
            
            else:
                raise ValueError(f"Unsupported operation: {operation}")
                
        except Exception as e:
            logger.error(f"MongoDB write operation failed: {e}")
            logger.error(f"Operation: {query}")
            logger.error(f"Parameters: {parameters}")
            raise
    
    async def create_table(self, table_name: str, schema: Dict[str, Any]) -> bool:
        """Create MongoDB collection with schema validation."""
        try:
            collection_name = table_name
            
            # Build JSON schema validation
            json_schema = self._build_json_schema(schema)
            
            # Create collection with validation
            await self.database.create_collection(
                collection_name,
                validator={'$jsonSchema': json_schema}
            )
            
            # Create indexes
            indexes = []
            for field_name, field_config in schema.items():
                if field_name == '_metadata':
                    continue
                
                if field_config.get('index'):
                    index_type = field_config.get('index_type', 'ascending')
                    if index_type == 'text':
                        indexes.append(IndexModel([(field_name, TEXT)]))
                    elif index_type == 'geo2d':
                        indexes.append(IndexModel([(field_name, GEO2D)]))
                    else:
                        direction = ASCENDING if index_type == 'ascending' else DESCENDING
                        indexes.append(IndexModel([(field_name, direction)]))
                
                if field_config.get('unique'):
                    indexes.append(IndexModel([(field_name, ASCENDING)], unique=True))
            
            if indexes:
                collection = self.database[collection_name]
                await collection.create_indexes(indexes)
            
            logger.info(f"Created MongoDB collection: {collection_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create collection {table_name}: {e}")
            return False
    
    def _build_json_schema(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Build MongoDB JSON schema from field definitions."""
        
        properties = {}
        required_fields = []
        
        for field_name, field_config in schema.items():
            if field_name == '_metadata':
                continue
            
            field_type = field_config.get('type', 'string')
            
            # Map Python types to JSON schema types
            type_mapping = {
                'str': 'string',
                'int': 'number',
                'float': 'number',
                'bool': 'boolean',
                'datetime': 'string',
                'date': 'string',
                'list': 'array',
                'dict': 'object',
                'json': 'object'
            }
            
            json_type = type_mapping.get(field_type.lower(), 'string')
            
            field_schema = {'type': json_type}
            
            # Add constraints
            if field_config.get('min_length'):
                field_schema['minLength'] = field_config['min_length']
            
            if field_config.get('max_length'):
                field_schema['maxLength'] = field_config['max_length']
            
            if field_config.get('pattern'):
                field_schema['pattern'] = field_config['pattern']
            
            if field_config.get('enum'):
                field_schema['enum'] = field_config['enum']
            
            properties[field_name] = field_schema
            
            if not field_config.get('nullable', True):
                required_fields.append(field_name)
        
        json_schema = {
            'type': 'object',
            'properties': properties
        }
        
        if required_fields:
            json_schema['required'] = required_fields
        
        return json_schema
    
    async def insert_bulk(self, table_name: str, data: List[Dict[str, Any]]) -> int:
        """Efficient bulk insert using MongoDB insert_many."""
        if not data:
            return 0
        
        try:
            collection = self.database[table_name]
            
            # Add timestamps
            for document in data:
                document.setdefault('created_at', datetime.utcnow())
                document.setdefault('updated_at', datetime.utcnow())
            
            result = await collection.insert_many(data, ordered=False)
            
            logger.info(f"Bulk inserted {len(result.inserted_ids)} documents into {table_name}")
            return len(result.inserted_ids)
            
        except Exception as e:
            logger.error(f"Bulk insert failed for {table_name}: {e}")
            raise
    
    async def create_collection(self, collection_name: str, schema: Optional[Dict[str, Any]] = None) -> bool:
        """Create a MongoDB collection."""
        return await self.create_table(collection_name, schema or {})
    
    async def insert_document(self, collection_name: str, document: Dict[str, Any]) -> str:
        """Insert a single document."""
        try:
            collection = self.database[collection_name]
            document.setdefault('created_at', datetime.utcnow())
            document.setdefault('updated_at', datetime.utcnow())
            
            result = await collection.insert_one(document)
            return str(result.inserted_id)
            
        except Exception as e:
            logger.error(f"Failed to insert document into {collection_name}: {e}")
            raise
    
    async def find_documents(self, collection_name: str, query: Dict[str, Any], limit: int = 100) -> List[Dict[str, Any]]:
        """Find documents matching query."""
        try:
            collection = self.database[collection_name]
            cursor = collection.find(query).limit(limit)
            
            results = []
            async for document in cursor:
                document['_id'] = str(document['_id'])
                results.append(document)
            
            return results
            
        except Exception as e:
            logger.error(f"Find documents failed for {collection_name}: {e}")
            raise
    
    async def aggregate(self, collection_name: str, pipeline: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Execute MongoDB aggregation pipeline."""
        try:
            collection = self.database[collection_name]
            cursor = collection.aggregate(pipeline)
            
            results = []
            async for document in cursor:
                if '_id' in document and isinstance(document['_id'], ObjectId):
                    document['_id'] = str(document['_id'])
                results.append(document)
            
            return results
            
        except Exception as e:
            logger.error(f"Aggregation failed for {collection_name}: {e}")
            raise
    
    async def create_text_index(self, collection_name: str, fields: List[str]) -> bool:
        """Create text index for full-text search."""
        try:
            collection = self.database[collection_name]
            index_spec = [(field, TEXT) for field in fields]
            await collection.create_index(index_spec)
            
            logger.info(f"Created text index on {collection_name}: {fields}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create text index: {e}")
            return False
    
    async def search_text(self, collection_name: str, query: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Perform text search."""
        try:
            collection = self.database[collection_name]
            cursor = collection.find(
                {'$text': {'$search': query}},
                {'score': {'$meta': 'textScore'}}
            ).sort([('score', {'$meta': 'textScore'})]).limit(limit)
            
            results = []
            async for document in cursor:
                document['_id'] = str(document['_id'])
                results.append(document)
            
            return results
            
        except Exception as e:
            logger.error(f"Text search failed for {collection_name}: {e}")
            raise
    
    async def create_geo_index(self, collection_name: str, field_name: str, index_type: str = '2dsphere') -> bool:
        """Create geospatial index."""
        try:
            collection = self.database[collection_name]
            
            if index_type == '2dsphere':
                await collection.create_index([(field_name, '2dsphere')])
            elif index_type == '2d':
                await collection.create_index([(field_name, GEO2D)])
            else:
                raise ValueError(f"Unsupported geo index type: {index_type}")
            
            logger.info(f"Created {index_type} index on {collection_name}.{field_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create geo index: {e}")
            return False
    
    async def find_near(self, collection_name: str, coordinates: List[float], max_distance: float, limit: int = 100) -> List[Dict[str, Any]]:
        """Find documents near geographic coordinates."""
        try:
            collection = self.database[collection_name]
            cursor = collection.find({
                'location': {
                    '$near': {
                        '$geometry': {
                            'type': 'Point',
                            'coordinates': coordinates
                        },
                        '$maxDistance': max_distance
                    }
                }
            }).limit(limit)
            
            results = []
            async for document in cursor:
                document['_id'] = str(document['_id'])
                results.append(document)
            
            return results
            
        except Exception as e:
            logger.error(f"Geospatial search failed for {collection_name}: {e}")
            raise
    
    async def get_table_schema(self, table_name: str) -> Dict[str, Any]:
        """Get collection schema and statistics."""
        try:
            collection = self.database[table_name]
            
            # Get collection stats
            stats = await self.database.command('collStats', table_name)
            
            # Get indexes
            indexes = []
            async for index in collection.list_indexes():
                indexes.append(index)
            
            # Sample document to infer schema
            sample_doc = await collection.find_one()
            inferred_schema = {}
            
            if sample_doc:
                for key, value in sample_doc.items():
                    if key == '_id':
                        continue
                    
                    inferred_schema[key] = {
                        'type': type(value).__name__,
                        'sample_value': str(value)[:100] if isinstance(value, str) else value
                    }
            
            return {
                'collection_name': table_name,
                'stats': stats,
                'indexes': indexes,
                'inferred_schema': inferred_schema,
                'document_count': stats.get('count', 0),
                'avg_document_size': stats.get('avgObjSize', 0),
                'total_size': stats.get('size', 0)
            }
            
        except Exception as e:
            logger.error(f"Failed to get schema for {table_name}: {e}")
            return {}
    
    async def list_tables(self) -> List[str]:
        """List all collections in the database."""
        try:
            collection_names = await self.database.list_collection_names()
            return sorted(collection_names)
            
        except Exception as e:
            logger.error(f"Failed to list collections: {e}")
            return []
    
    async def export_collection(self, collection_name: str, output_format: str = 'json') -> str:
        """Export collection data."""
        try:
            collection = self.database[collection_name]
            documents = []
            
            async for doc in collection.find():
                documents.append(doc)
            
            if output_format == 'json':
                return json_util.dumps(documents, indent=2)
            else:
                raise ValueError(f"Unsupported export format: {output_format}")
                
        except Exception as e:
            logger.error(f"Export failed for {collection_name}: {e}")
            raise
    
    async def watch_changes(self, collection_name: str, pipeline: Optional[List[Dict[str, Any]]] = None):
        """Watch for changes in collection (change streams)."""
        try:
            collection = self.database[collection_name]
            
            if pipeline:
                change_stream = collection.watch(pipeline)
            else:
                change_stream = collection.watch()
            
            async for change in change_stream:
                yield change
                
        except Exception as e:
            logger.error(f"Change stream failed for {collection_name}: {e}")
            raise
    
    async def health_check(self) -> Dict[str, Any]:
        """Comprehensive health check."""
        try:
            start_time = datetime.now()
            
            # Basic ping test
            await self.client.admin.command('ping')
            
            # Performance test
            query_start = datetime.now()
            await self.database.command('dbStats')
            query_time = (datetime.now() - query_start).total_seconds()
            
            # Get server status
            server_status = await self.client.admin.command('serverStatus')
            db_stats = await self.database.command('dbStats')
            
            # Get collection count
            collections = await self.database.list_collection_names()
            
            health_check_time = (datetime.now() - start_time).total_seconds()
            
            return {
                'status': 'healthy',
                'version': server_status.get('version', 'unknown'),
                'uptime_seconds': server_status.get('uptime', 0),
                'database_size_bytes': db_stats.get('dataSize', 0),
                'collection_count': len(collections),
                'active_connections': server_status.get('connections', {}).get('current', 0),
                'available_connections': server_status.get('connections', {}).get('available', 0),
                'query_response_time_ms': query_time * 1000,
                'health_check_time_ms': health_check_time * 1000,
                'memory_usage_mb': server_status.get('mem', {}).get('resident', 0),
                'network_requests': server_status.get('network', {}).get('numRequests', 0),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }