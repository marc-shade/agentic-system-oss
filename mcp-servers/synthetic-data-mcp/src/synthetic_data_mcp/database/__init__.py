"""
Database connectors and management for enterprise-grade storage.

This package provides comprehensive database connectivity for:
- PostgreSQL (primary production database)
- MySQL (compatibility and migration support)
- MongoDB (document storage)
- Redis (caching and sessions)
- Cloud databases (BigQuery, Snowflake, Redshift)
"""

from .connectors.postgresql import PostgreSQLConnector
from .connectors.mysql import MySQLConnector
from .connectors.mongodb import MongoDBConnector
from .connectors.bigquery import BigQueryConnector
from .connectors.snowflake import SnowflakeConnector
from .connectors.redshift import RedshiftConnector

# Redis connector temporarily disabled due to aioredis compatibility issues
try:
    from .connectors.redis import RedisConnector
    REDIS_AVAILABLE = True
except ImportError:
    RedisConnector = None
    REDIS_AVAILABLE = False
from .manager import DatabaseManager
from .migrations import MigrationManager
from .schema_inspector import SchemaInspector

__all__ = [
    'PostgreSQLConnector',
    'MySQLConnector', 
    'MongoDBConnector',
    'BigQueryConnector',
    'SnowflakeConnector', 
    'RedshiftConnector',
    'DatabaseManager',
    'MigrationManager',
    'SchemaInspector'
]

# Add Redis to exports only if available
if REDIS_AVAILABLE:
    __all__.append('RedisConnector')