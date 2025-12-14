"""
Database connector implementations for multiple database systems.
"""

# Import all connectors for easy access
from .postgresql import PostgreSQLConnector
from .mysql import MySQLConnector
from .mongodb import MongoDBConnector
from .bigquery import BigQueryConnector
from .snowflake import SnowflakeConnector
from .redshift import RedshiftConnector

# Redis connector - temporarily disabled due to aioredis compatibility issues with Python 3.12
# TODO: Fix aioredis compatibility or replace with redis-py
RedisConnector = None
REDIS_AVAILABLE = False
# Warning: Redis connector disabled due to aioredis compatibility issues with Python 3.12

__all__ = [
    'PostgreSQLConnector',
    'MySQLConnector',
    'MongoDBConnector', 
    'BigQueryConnector',
    'SnowflakeConnector',
    'RedshiftConnector'
]

# Add Redis to exports only if available
if REDIS_AVAILABLE:
    __all__.append('RedisConnector')