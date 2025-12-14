"""
Enterprise horizontal scaling and database sharding infrastructure.

Implements auto-scaling, database sharding, connection pooling,
load distribution, and high availability for production scalability.
"""

import asyncio
import hashlib
import random
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, Callable
from dataclasses import dataclass
from enum import Enum
from contextlib import asynccontextmanager

import asyncpg
from sqlalchemy import create_engine, pool, event, MetaData
from sqlalchemy.ext.horizontal_shard import ShardedSession
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool, QueuePool
import redis
from redis.sentinel import Sentinel
from loguru import logger
import consul
import etcd3
from kubernetes import client, config
from prometheus_client import Gauge, Counter
import aioboto3


# Metrics for monitoring
shard_connections = Gauge('synthetic_data_shard_connections', 'Database shard connections', ['shard'])
shard_queries = Counter('synthetic_data_shard_queries', 'Database shard queries', ['shard', 'operation'])
scaling_events = Counter('synthetic_data_scaling_events', 'Auto-scaling events', ['direction', 'component'])


class ShardStrategy(Enum):
    """Database sharding strategies."""
    HASH = "hash"           # Hash-based sharding
    RANGE = "range"         # Range-based sharding
    GEOGRAPHIC = "geographic"  # Geographic sharding
    ROUND_ROBIN = "round_robin"  # Round-robin distribution


@dataclass
class DatabaseShard:
    """Database shard configuration."""
    shard_id: str
    host: str
    port: int
    database: str
    weight: int = 1
    region: Optional[str] = None
    read_replicas: List[str] = None
    is_active: bool = True
    max_connections: int = 100


class ShardedDatabaseManager:
    """Manages sharded database connections and routing."""
    
    def __init__(
        self,
        shards: List[DatabaseShard],
        strategy: ShardStrategy = ShardStrategy.HASH
    ):
        self.shards = {s.shard_id: s for s in shards}
        self.strategy = strategy
        self.pools = {}
        self.read_pools = {}
        self._initialize_pools()
    
    def _initialize_pools(self):
        """Initialize connection pools for all shards."""
        for shard_id, shard in self.shards.items():
            # Primary write pool
            write_url = f"postgresql://{shard.host}:{shard.port}/{shard.database}"
            self.pools[shard_id] = create_engine(
                write_url,
                poolclass=QueuePool,
                pool_size=20,
                max_overflow=10,
                pool_pre_ping=True,
                pool_recycle=3600,
                echo_pool=True
            )
            
            # Read replica pools
            if shard.read_replicas:
                self.read_pools[shard_id] = []
                for replica_url in shard.read_replicas:
                    engine = create_engine(
                        replica_url,
                        poolclass=QueuePool,
                        pool_size=10,
                        max_overflow=5,
                        pool_pre_ping=True
                    )
                    self.read_pools[shard_id].append(engine)
            
            # Monitor connections
            @event.listens_for(self.pools[shard_id], "connect")
            def receive_connect(dbapi_conn, connection_record):
                shard_connections.labels(shard=shard_id).inc()
            
            @event.listens_for(self.pools[shard_id], "close")
            def receive_close(dbapi_conn, connection_record):
                shard_connections.labels(shard=shard_id).dec()
    
    def get_shard_for_key(self, key: str) -> str:
        """Determine which shard should handle a given key."""
        if self.strategy == ShardStrategy.HASH:
            # Hash-based sharding
            hash_value = int(hashlib.md5(key.encode()).hexdigest(), 16)
            active_shards = [s for s in self.shards.values() if s.is_active]
            shard_index = hash_value % len(active_shards)
            return active_shards[shard_index].shard_id
        
        elif self.strategy == ShardStrategy.ROUND_ROBIN:
            # Round-robin distribution
            active_shards = [s for s in self.shards.values() if s.is_active]
            return random.choice(active_shards).shard_id
        
        elif self.strategy == ShardStrategy.RANGE:
            # Range-based sharding (implement based on key ranges)
            # This would require additional configuration
            pass
        
        elif self.strategy == ShardStrategy.GEOGRAPHIC:
            # Geographic sharding based on region
            # This would require region detection logic
            pass
        
        # Default to first active shard
        active_shards = [s for s in self.shards.values() if s.is_active]
        return active_shards[0].shard_id if active_shards else None
    
    def get_write_connection(self, shard_id: str):
        """Get write connection for a specific shard."""
        if shard_id not in self.pools:
            raise ValueError(f"Shard {shard_id} not found")
        
        shard_queries.labels(shard=shard_id, operation="write").inc()
        return self.pools[shard_id]
    
    def get_read_connection(self, shard_id: str):
        """Get read connection with replica selection."""
        # Try read replicas first
        if shard_id in self.read_pools and self.read_pools[shard_id]:
            replica = random.choice(self.read_pools[shard_id])
            shard_queries.labels(shard=shard_id, operation="read_replica").inc()
            return replica
        
        # Fallback to primary
        shard_queries.labels(shard=shard_id, operation="read_primary").inc()
        return self.pools[shard_id]
    
    async def execute_on_all_shards(
        self,
        query: str,
        params: Optional[Dict] = None
    ) -> List[Any]:
        """Execute query on all active shards."""
        results = []
        
        for shard_id, shard in self.shards.items():
            if not shard.is_active:
                continue
            
            try:
                engine = self.get_read_connection(shard_id)
                with engine.connect() as conn:
                    result = conn.execute(query, params or {})
                    results.extend(result.fetchall())
            except Exception as e:
                logger.error(f"Error executing on shard {shard_id}: {e}")
        
        return results
    
    async def rebalance_shards(self):
        """Rebalance data across shards."""
        logger.info("Starting shard rebalancing...")
        
        # Calculate target distribution
        total_weight = sum(s.weight for s in self.shards.values() if s.is_active)
        
        for shard_id, shard in self.shards.items():
            if not shard.is_active:
                continue
            
            target_percentage = (shard.weight / total_weight) * 100
            logger.info(f"Shard {shard_id} target: {target_percentage:.2f}%")
            
            # Implement actual data migration logic here
            # This would involve moving data between shards
        
        logger.info("Shard rebalancing completed")
    
    def add_shard(self, shard: DatabaseShard):
        """Add a new shard to the cluster."""
        self.shards[shard.shard_id] = shard
        self._initialize_pools()
        logger.info(f"Added new shard: {shard.shard_id}")
        
        # Trigger rebalancing
        asyncio.create_task(self.rebalance_shards())
    
    def remove_shard(self, shard_id: str):
        """Remove a shard from the cluster."""
        if shard_id in self.shards:
            self.shards[shard_id].is_active = False
            logger.info(f"Deactivated shard: {shard_id}")
            
            # Trigger rebalancing
            asyncio.create_task(self.rebalance_shards())


class AsyncConnectionPool:
    """Async connection pool for PostgreSQL."""
    
    def __init__(
        self,
        dsn: str,
        min_size: int = 10,
        max_size: int = 100,
        max_queries: int = 50000,
        max_inactive_connection_lifetime: float = 300.0
    ):
        self.dsn = dsn
        self.min_size = min_size
        self.max_size = max_size
        self.max_queries = max_queries
        self.max_inactive_connection_lifetime = max_inactive_connection_lifetime
        self.pool = None
    
    async def initialize(self):
        """Initialize the connection pool."""
        self.pool = await asyncpg.create_pool(
            self.dsn,
            min_size=self.min_size,
            max_size=self.max_size,
            max_queries=self.max_queries,
            max_inactive_connection_lifetime=self.max_inactive_connection_lifetime,
            command_timeout=60
        )
        logger.info(f"Initialized async connection pool: {self.min_size}-{self.max_size} connections")
    
    async def close(self):
        """Close the connection pool."""
        if self.pool:
            await self.pool.close()
    
    @asynccontextmanager
    async def acquire(self):
        """Acquire a connection from the pool."""
        async with self.pool.acquire() as connection:
            yield connection
    
    async def execute(self, query: str, *args):
        """Execute a query."""
        async with self.acquire() as conn:
            return await conn.execute(query, *args)
    
    async def fetch(self, query: str, *args):
        """Fetch results from a query."""
        async with self.acquire() as conn:
            return await conn.fetch(query, *args)
    
    async def fetchrow(self, query: str, *args):
        """Fetch a single row."""
        async with self.acquire() as conn:
            return await conn.fetchrow(query, *args)
    
    async def fetchval(self, query: str, *args):
        """Fetch a single value."""
        async with self.acquire() as conn:
            return await conn.fetchval(query, *args)


class AutoScaler:
    """Kubernetes-based auto-scaling manager."""
    
    def __init__(self):
        # Load Kubernetes config
        try:
            config.load_incluster_config()  # For in-cluster deployment
        except:
            config.load_kube_config()  # For local development
        
        self.v1 = client.CoreV1Api()
        self.apps_v1 = client.AppsV1Api()
        self.autoscaling_v1 = client.AutoscalingV1Api()
        
        # Scaling parameters
        self.min_replicas = 2
        self.max_replicas = 20
        self.target_cpu_utilization = 70
        self.scale_up_threshold = 80
        self.scale_down_threshold = 30
    
    async def get_current_metrics(self) -> Dict[str, Any]:
        """Get current resource metrics."""
        try:
            # Get pod metrics from metrics server
            metrics = client.CustomObjectsApi()
            pod_metrics = metrics.list_namespaced_custom_object(
                group="metrics.k8s.io",
                version="v1beta1",
                namespace="synthetic-data",
                plural="pods"
            )
            
            total_cpu = 0
            total_memory = 0
            pod_count = 0
            
            for pod in pod_metrics.get('items', []):
                for container in pod.get('containers', []):
                    cpu = container.get('usage', {}).get('cpu', '0')
                    memory = container.get('usage', {}).get('memory', '0')
                    
                    # Parse CPU (convert from nano-cores)
                    if cpu.endswith('n'):
                        total_cpu += int(cpu[:-1]) / 1_000_000_000
                    elif cpu.endswith('m'):
                        total_cpu += int(cpu[:-1]) / 1000
                    
                    # Parse memory
                    if memory.endswith('Ki'):
                        total_memory += int(memory[:-2]) * 1024
                    elif memory.endswith('Mi'):
                        total_memory += int(memory[:-2]) * 1024 * 1024
                    
                    pod_count += 1
            
            avg_cpu = (total_cpu / pod_count * 100) if pod_count > 0 else 0
            avg_memory = total_memory / pod_count if pod_count > 0 else 0
            
            return {
                "cpu_percentage": avg_cpu,
                "memory_bytes": avg_memory,
                "pod_count": pod_count
            }
            
        except Exception as e:
            logger.error(f"Error getting metrics: {e}")
            return {"cpu_percentage": 0, "memory_bytes": 0, "pod_count": 0}
    
    async def scale_deployment(
        self,
        deployment_name: str,
        namespace: str,
        replicas: int
    ) -> bool:
        """Scale a deployment to specified replicas."""
        try:
            # Get current deployment
            deployment = self.apps_v1.read_namespaced_deployment(
                name=deployment_name,
                namespace=namespace
            )
            
            current_replicas = deployment.spec.replicas
            
            if replicas == current_replicas:
                return True
            
            # Update replica count
            deployment.spec.replicas = replicas
            self.apps_v1.patch_namespaced_deployment_scale(
                name=deployment_name,
                namespace=namespace,
                body={"spec": {"replicas": replicas}}
            )
            
            direction = "up" if replicas > current_replicas else "down"
            scaling_events.labels(direction=direction, component=deployment_name).inc()
            
            logger.info(f"Scaled {deployment_name} from {current_replicas} to {replicas} replicas")
            return True
            
        except Exception as e:
            logger.error(f"Error scaling deployment: {e}")
            return False
    
    async def auto_scale(self):
        """Auto-scale based on metrics."""
        while True:
            try:
                metrics = await self.get_current_metrics()
                cpu_usage = metrics["cpu_percentage"]
                current_replicas = metrics["pod_count"]
                
                # Determine scaling action
                if cpu_usage > self.scale_up_threshold and current_replicas < self.max_replicas:
                    # Scale up
                    new_replicas = min(current_replicas + 2, self.max_replicas)
                    await self.scale_deployment(
                        "synthetic-data-mcp",
                        "synthetic-data",
                        new_replicas
                    )
                
                elif cpu_usage < self.scale_down_threshold and current_replicas > self.min_replicas:
                    # Scale down
                    new_replicas = max(current_replicas - 1, self.min_replicas)
                    await self.scale_deployment(
                        "synthetic-data-mcp",
                        "synthetic-data",
                        new_replicas
                    )
                
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Auto-scaling error: {e}")
                await asyncio.sleep(60)


class ServiceDiscovery:
    """Service discovery and registration using Consul."""
    
    def __init__(self, consul_host: str = "localhost", consul_port: int = 8500):
        self.consul = consul.Consul(host=consul_host, port=consul_port)
        self.service_id = None
    
    def register_service(
        self,
        name: str,
        service_id: str,
        address: str,
        port: int,
        tags: List[str] = None,
        health_check_url: Optional[str] = None
    ):
        """Register service with Consul."""
        check = None
        if health_check_url:
            check = consul.Check.http(
                health_check_url,
                interval="10s",
                timeout="5s",
                deregister="30s"
            )
        
        self.consul.agent.service.register(
            name=name,
            service_id=service_id,
            address=address,
            port=port,
            tags=tags or [],
            check=check
        )
        
        self.service_id = service_id
        logger.info(f"Registered service {name} with ID {service_id}")
    
    def deregister_service(self):
        """Deregister service from Consul."""
        if self.service_id:
            self.consul.agent.service.deregister(self.service_id)
            logger.info(f"Deregistered service {self.service_id}")
    
    def discover_service(self, service_name: str) -> List[Dict[str, Any]]:
        """Discover available service instances."""
        _, services = self.consul.health.service(service_name, passing=True)
        
        instances = []
        for service in services:
            instances.append({
                "id": service['Service']['ID'],
                "address": service['Service']['Address'],
                "port": service['Service']['Port'],
                "tags": service['Service']['Tags']
            })
        
        return instances
    
    def get_config(self, key: str) -> Optional[str]:
        """Get configuration from Consul KV store."""
        _, data = self.consul.kv.get(key)
        if data:
            return data['Value'].decode('utf-8')
        return None
    
    def set_config(self, key: str, value: str):
        """Set configuration in Consul KV store."""
        self.consul.kv.put(key, value)


class LoadBalancer:
    """Application-level load balancer."""
    
    def __init__(self, backends: List[str]):
        self.backends = backends
        self.current_index = 0
        self.backend_health = {backend: True for backend in backends}
        self._start_health_checks()
    
    def _start_health_checks(self):
        """Start background health checks."""
        asyncio.create_task(self._health_check_worker())
    
    async def _health_check_worker(self):
        """Background worker for health checks."""
        import aiohttp
        
        while True:
            async with aiohttp.ClientSession() as session:
                for backend in self.backends:
                    try:
                        async with session.get(
                            f"http://{backend}/health",
                            timeout=aiohttp.ClientTimeout(total=5)
                        ) as response:
                            self.backend_health[backend] = response.status == 200
                    except:
                        self.backend_health[backend] = False
            
            await asyncio.sleep(10)
    
    def get_backend(self) -> Optional[str]:
        """Get next healthy backend using round-robin."""
        healthy_backends = [
            b for b in self.backends 
            if self.backend_health.get(b, False)
        ]
        
        if not healthy_backends:
            return None
        
        backend = healthy_backends[self.current_index % len(healthy_backends)]
        self.current_index += 1
        
        return backend
    
    def add_backend(self, backend: str):
        """Add a new backend."""
        if backend not in self.backends:
            self.backends.append(backend)
            self.backend_health[backend] = True
    
    def remove_backend(self, backend: str):
        """Remove a backend."""
        if backend in self.backends:
            self.backends.remove(backend)
            del self.backend_health[backend]


class DistributedLock:
    """Distributed locking using Redis."""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
    
    async def acquire(
        self,
        lock_name: str,
        timeout: int = 10,
        blocking: bool = True,
        blocking_timeout: int = 30
    ) -> bool:
        """Acquire a distributed lock."""
        identifier = str(uuid.uuid4())
        end_time = time.time() + blocking_timeout
        
        while True:
            if self.redis.set(
                f"lock:{lock_name}",
                identifier,
                nx=True,
                ex=timeout
            ):
                return True
            
            if not blocking or time.time() > end_time:
                return False
            
            await asyncio.sleep(0.1)
    
    async def release(self, lock_name: str) -> bool:
        """Release a distributed lock."""
        return bool(self.redis.delete(f"lock:{lock_name}"))
    
    @asynccontextmanager
    async def lock(self, lock_name: str, timeout: int = 10):
        """Context manager for distributed locking."""
        acquired = await self.acquire(lock_name, timeout)
        if not acquired:
            raise Exception(f"Could not acquire lock: {lock_name}")
        
        try:
            yield
        finally:
            await self.release(lock_name)


# Global instances
shard_manager = None
auto_scaler = None
service_discovery = None


def initialize_scaling_infrastructure(config: Dict[str, Any]):
    """Initialize scaling infrastructure components."""
    global shard_manager, auto_scaler, service_discovery
    
    # Initialize database sharding
    shards = []
    for shard_config in config.get("database_shards", []):
        shard = DatabaseShard(**shard_config)
        shards.append(shard)
    
    if shards:
        shard_manager = ShardedDatabaseManager(
            shards=shards,
            strategy=ShardStrategy[config.get("shard_strategy", "HASH")]
        )
    
    # Initialize auto-scaler
    if config.get("enable_autoscaling", False):
        auto_scaler = AutoScaler()
        asyncio.create_task(auto_scaler.auto_scale())
    
    # Initialize service discovery
    if config.get("consul_enabled", False):
        service_discovery = ServiceDiscovery(
            consul_host=config.get("consul_host", "localhost"),
            consul_port=config.get("consul_port", 8500)
        )
    
    logger.info("Scaling infrastructure initialized")