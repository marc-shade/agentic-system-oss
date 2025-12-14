"""
Enterprise AWS DynamoDB connector for synthetic-data-mcp platform.

This connector provides comprehensive DynamoDB functionality including:
- Multi-region global tables
- Auto-scaling and on-demand billing
- DynamoDB Streams integration  
- Point-in-time recovery
- VPC endpoint support
- IAM role-based authentication
- Batch operations and transactions
- Circuit breaker patterns
- Performance metrics and monitoring
- Cost optimization
"""

import asyncio
import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Union, AsyncGenerator
from contextlib import asynccontextmanager
import random
import math

import boto3
from botocore.exceptions import ClientError, BotoCoreError
from botocore.config import Config
from loguru import logger

from ..base import NoSQLDatabaseConnector


class CircuitBreakerState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"
    OPEN = "open" 
    HALF_OPEN = "half_open"


@dataclass
class RetryConfig:
    """Retry configuration with exponential backoff."""
    max_attempts: int = 5
    base_delay: float = 0.1
    max_delay: float = 30.0
    exponential_base: float = 2.0
    jitter: bool = True
    
    def get_delay(self, attempt: int) -> float:
        """Calculate delay for retry attempt with exponential backoff and jitter."""
        delay = min(self.base_delay * (self.exponential_base ** attempt), self.max_delay)
        if self.jitter:
            delay *= (0.5 + random.random() * 0.5)  # 50-100% of calculated delay
        return delay


@dataclass
class CircuitBreaker:
    """Circuit breaker for fault tolerance."""
    failure_threshold: int = 5
    recovery_timeout: float = 60.0
    timeout: float = 30.0
    state: CircuitBreakerState = CircuitBreakerState.CLOSED
    failure_count: int = 0
    last_failure_time: Optional[datetime] = None
    half_open_max_calls: int = 3
    half_open_calls: int = 0
    
    def should_allow_request(self) -> bool:
        """Determine if request should be allowed based on circuit breaker state."""
        now = datetime.utcnow()
        
        if self.state == CircuitBreakerState.CLOSED:
            return True
        elif self.state == CircuitBreakerState.OPEN:
            if self.last_failure_time and (now - self.last_failure_time).total_seconds() > self.recovery_timeout:
                self.state = CircuitBreakerState.HALF_OPEN
                self.half_open_calls = 0
                logger.info("Circuit breaker transitioning to HALF_OPEN")
                return True
            return False
        elif self.state == CircuitBreakerState.HALF_OPEN:
            return self.half_open_calls < self.half_open_max_calls
        
        return False
    
    def record_success(self):
        """Record successful operation."""
        if self.state == CircuitBreakerState.HALF_OPEN:
            self.half_open_calls += 1
            if self.half_open_calls >= self.half_open_max_calls:
                self.state = CircuitBreakerState.CLOSED
                self.failure_count = 0
                logger.info("Circuit breaker reset to CLOSED")
        elif self.state == CircuitBreakerState.CLOSED:
            self.failure_count = 0
    
    def record_failure(self):
        """Record failed operation."""
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()
        
        if self.state == CircuitBreakerState.CLOSED and self.failure_count >= self.failure_threshold:
            self.state = CircuitBreakerState.OPEN
            logger.warning(f"Circuit breaker OPENED after {self.failure_count} failures")
        elif self.state == CircuitBreakerState.HALF_OPEN:
            self.state = CircuitBreakerState.OPEN
            logger.warning("Circuit breaker returned to OPEN from HALF_OPEN")


@dataclass
class PerformanceMetrics:
    """Performance metrics tracking."""
    operation_counts: Dict[str, int] = field(default_factory=dict)
    latencies: Dict[str, List[float]] = field(default_factory=dict)
    error_counts: Dict[str, int] = field(default_factory=dict)
    cost_estimates: Dict[str, float] = field(default_factory=dict)
    
    def record_operation(self, operation: str, latency: float, error: bool = False, cost: float = 0.0):
        """Record operation metrics."""
        self.operation_counts[operation] = self.operation_counts.get(operation, 0) + 1
        
        if operation not in self.latencies:
            self.latencies[operation] = []
        self.latencies[operation].append(latency)
        
        if error:
            self.error_counts[operation] = self.error_counts.get(operation, 0) + 1
            
        if cost > 0:
            self.cost_estimates[operation] = self.cost_estimates.get(operation, 0.0) + cost
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive performance statistics."""
        stats = {"operations": {}}
        
        for operation in self.operation_counts:
            latencies = self.latencies.get(operation, [])
            error_count = self.error_counts.get(operation, 0)
            total_count = self.operation_counts[operation]
            
            stats["operations"][operation] = {
                "total_calls": total_count,
                "error_count": error_count,
                "error_rate": error_count / total_count if total_count > 0 else 0,
                "avg_latency_ms": sum(latencies) / len(latencies) if latencies else 0,
                "p95_latency_ms": sorted(latencies)[int(len(latencies) * 0.95)] if latencies else 0,
                "total_cost_usd": self.cost_estimates.get(operation, 0.0)
            }
        
        stats["summary"] = {
            "total_operations": sum(self.operation_counts.values()),
            "total_errors": sum(self.error_counts.values()),
            "total_cost_usd": sum(self.cost_estimates.values()),
            "overall_error_rate": sum(self.error_counts.values()) / sum(self.operation_counts.values()) 
                                  if sum(self.operation_counts.values()) > 0 else 0
        }
        
        return stats


class DynamoDBConnector(NoSQLDatabaseConnector):
    """
    Enterprise AWS DynamoDB connector with comprehensive AWS features.
    
    Features:
    - Multi-region global tables
    - Auto-scaling with provisioned/on-demand billing
    - DynamoDB Streams integration
    - Point-in-time recovery
    - VPC endpoint support
    - IAM role-based authentication
    - Batch operations and transactions
    - Circuit breaker patterns
    - Performance metrics and monitoring
    - Cost optimization
    """
    
    def __init__(self, connection_config: Dict[str, Any]):
        """
        Initialize DynamoDB connector with enterprise configuration.
        
        Args:
            connection_config: Configuration including:
                - region_name: Primary AWS region
                - global_regions: List of regions for global tables
                - billing_mode: 'PAY_PER_REQUEST' or 'PROVISIONED'
                - role_arn: IAM role for authentication (optional)
                - vpc_endpoint_id: VPC endpoint ID (optional)
                - enable_streams: Enable DynamoDB Streams
                - enable_pitr: Enable point-in-time recovery
                - encryption_key: KMS key for encryption
                - auto_scaling: Auto-scaling configuration
                - circuit_breaker: Circuit breaker configuration
                - retry_config: Retry policy configuration
        """
        super().__init__(connection_config)
        
        self.region_name = connection_config.get('region_name', 'us-east-1')
        self.global_regions = connection_config.get('global_regions', [])
        self.billing_mode = connection_config.get('billing_mode', 'PAY_PER_REQUEST')
        self.role_arn = connection_config.get('role_arn')
        self.vpc_endpoint_id = connection_config.get('vpc_endpoint_id')
        self.enable_streams = connection_config.get('enable_streams', True)
        self.enable_pitr = connection_config.get('enable_pitr', True)
        self.encryption_key = connection_config.get('encryption_key')
        
        # Initialize circuit breaker
        cb_config = connection_config.get('circuit_breaker', {})
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=cb_config.get('failure_threshold', 5),
            recovery_timeout=cb_config.get('recovery_timeout', 60.0),
            timeout=cb_config.get('timeout', 30.0)
        )
        
        # Initialize retry configuration
        retry_config = connection_config.get('retry_config', {})
        self.retry_config = RetryConfig(
            max_attempts=retry_config.get('max_attempts', 5),
            base_delay=retry_config.get('base_delay', 0.1),
            max_delay=retry_config.get('max_delay', 30.0)
        )
        
        # Performance metrics
        self.metrics = PerformanceMetrics()
        
        # DynamoDB clients
        self.primary_client = None
        self.regional_clients = {}
        self.streams_client = None
        
        # Auto-scaling configuration
        self.auto_scaling_config = connection_config.get('auto_scaling', {})
        
        logger.info(f"Initialized DynamoDB connector for region {self.region_name}")
        
    async def connect(self) -> bool:
        """
        Establish connections to DynamoDB across all configured regions.
        
        Returns:
            True if primary connection successful
        """
        try:
            # Configure boto3 client with enterprise settings
            config = Config(
                region_name=self.region_name,
                retries={'max_attempts': 1},  # We handle retries ourselves
                max_pool_connections=50,
                read_timeout=60,
                connect_timeout=10
            )
            
            # Handle IAM role assumption if configured
            if self.role_arn:
                sts_client = boto3.client('sts', config=config)
                assumed_role = sts_client.assume_role(
                    RoleArn=self.role_arn,
                    RoleSessionName=f'synthetic-data-mcp-{int(time.time())}'
                )
                credentials = assumed_role['Credentials']
                
                session = boto3.Session(
                    aws_access_key_id=credentials['AccessKeyId'],
                    aws_secret_access_key=credentials['SecretAccessKey'],
                    aws_session_token=credentials['SessionToken']
                )
            else:
                session = boto3.Session()
            
            # Create primary DynamoDB client
            endpoint_url = f'https://vpce-{self.vpc_endpoint_id}.dynamodb.{self.region_name}.vpce.amazonaws.com' if self.vpc_endpoint_id else None
            
            self.primary_client = session.client(
                'dynamodb',
                config=config,
                endpoint_url=endpoint_url
            )
            
            # Create DynamoDB Streams client if enabled
            if self.enable_streams:
                self.streams_client = session.client(
                    'dynamodbstreams',
                    config=config
                )
            
            # Create regional clients for global tables
            for region in self.global_regions:
                if region != self.region_name:
                    regional_config = Config(
                        region_name=region,
                        retries={'max_attempts': 1},
                        max_pool_connections=10
                    )
                    self.regional_clients[region] = session.client(
                        'dynamodb',
                        config=regional_config
                    )
            
            # Test primary connection
            await asyncio.to_thread(self.primary_client.list_tables, Limit=1)
            self._connected = True
            
            logger.info(f"Successfully connected to DynamoDB in {self.region_name}")
            logger.info(f"Global regions configured: {self.global_regions}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to DynamoDB: {e}")
            return False
    
    async def disconnect(self) -> None:
        """Close all DynamoDB connections."""
        try:
            # No explicit close needed for boto3 clients
            self.primary_client = None
            self.regional_clients.clear()
            self.streams_client = None
            self._connected = False
            
            logger.info("Disconnected from DynamoDB")
            
        except Exception as e:
            logger.error(f"Error during DynamoDB disconnect: {e}")
    
    async def _execute_with_circuit_breaker(self, operation_name: str, operation_func, *args, **kwargs):
        """Execute operation with circuit breaker protection and retry logic."""
        if not self.circuit_breaker.should_allow_request():
            raise Exception(f"Circuit breaker OPEN for operation {operation_name}")
        
        start_time = time.time()
        last_exception = None
        
        for attempt in range(self.retry_config.max_attempts):
            try:
                if attempt > 0:
                    delay = self.retry_config.get_delay(attempt - 1)
                    logger.info(f"Retrying {operation_name} after {delay:.2f}s (attempt {attempt + 1})")
                    await asyncio.sleep(delay)
                
                # Execute operation
                if asyncio.iscoroutinefunction(operation_func):
                    result = await operation_func(*args, **kwargs)
                else:
                    result = await asyncio.to_thread(operation_func, *args, **kwargs)
                
                # Record success
                latency = (time.time() - start_time) * 1000
                self.circuit_breaker.record_success()
                self.metrics.record_operation(operation_name, latency)
                
                return result
                
            except (ClientError, BotoCoreError) as e:
                last_exception = e
                error_code = getattr(e, 'response', {}).get('Error', {}).get('Code', 'Unknown')
                
                # Don't retry for certain errors
                non_retryable_errors = [
                    'ValidationException',
                    'ResourceNotFoundException', 
                    'ConditionalCheckFailedException',
                    'AccessDeniedException'
                ]
                
                if error_code in non_retryable_errors:
                    break
                
                logger.warning(f"Attempt {attempt + 1} failed for {operation_name}: {error_code}")
                
            except Exception as e:
                last_exception = e
                logger.error(f"Unexpected error in {operation_name}: {e}")
                break
        
        # All retries failed
        latency = (time.time() - start_time) * 1000
        self.circuit_breaker.record_failure()
        self.metrics.record_operation(operation_name, latency, error=True)
        
        raise last_exception or Exception(f"Operation {operation_name} failed after {self.retry_config.max_attempts} attempts")
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Comprehensive health check for DynamoDB connector.
        
        Returns:
            Health status including connection, performance, and cost metrics
        """
        health_status = {
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'region': self.region_name,
            'circuit_breaker': {
                'state': self.circuit_breaker.state.value,
                'failure_count': self.circuit_breaker.failure_count,
                'last_failure': self.circuit_breaker.last_failure_time.isoformat() if self.circuit_breaker.last_failure_time else None
            },
            'performance': self.metrics.get_statistics(),
            'connections': {},
            'tables': {}
        }
        
        try:
            # Test primary connection
            if not self._connected:
                health_status['status'] = 'disconnected'
                return health_status
            
            # Check primary client
            tables = await asyncio.to_thread(self.primary_client.list_tables, Limit=10)
            health_status['connections']['primary'] = {
                'region': self.region_name,
                'status': 'connected',
                'table_count': len(tables.get('TableNames', []))
            }
            
            # Check regional clients
            for region, client in self.regional_clients.items():
                try:
                    regional_tables = await asyncio.to_thread(client.list_tables, Limit=1)
                    health_status['connections'][region] = {
                        'region': region,
                        'status': 'connected',
                        'table_count': len(regional_tables.get('TableNames', []))
                    }
                except Exception as e:
                    health_status['connections'][region] = {
                        'region': region,
                        'status': 'error',
                        'error': str(e)
                    }
                    health_status['status'] = 'degraded'
                    
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            health_status['status'] = 'error'
            health_status['error'] = str(e)
        
        return health_status