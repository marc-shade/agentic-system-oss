"""
Enterprise caching and rate limiting infrastructure.

Implements multi-tier caching, intelligent cache invalidation,
rate limiting, and request throttling for production scalability.
"""

import json
import hashlib
import pickle
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, Callable
from functools import wraps
from dataclasses import dataclass
from enum import Enum

import redis
from redis.sentinel import Sentinel
import aiocache
from aiocache import Cache
from aiocache.serializers import JsonSerializer, PickleSerializer
from loguru import logger
import asyncio
from collections import defaultdict
import lru


# Redis configuration for high availability
REDIS_SENTINELS = [
    ('localhost', 26379),
    ('localhost', 26380),
    ('localhost', 26381),
]

# Initialize Redis clients
try:
    # Try Sentinel for HA
    sentinel = Sentinel(REDIS_SENTINELS, socket_timeout=0.1)
    redis_master = sentinel.master_for('mymaster', socket_timeout=0.1)
    redis_slave = sentinel.slave_for('mymaster', socket_timeout=0.1)
except:
    # Fallback to single instance
    redis_master = redis.Redis(host='localhost', port=6379, decode_responses=True)
    redis_slave = redis_master

# Memory cache configuration
memory_cache = Cache(Cache.MEMORY)
memory_cache.serializer = JsonSerializer()

# Disk cache for large objects
disk_cache = Cache(
    Cache.DISK,
    serializer=PickleSerializer(),
    namespace="synthetic_data",
    directory="/tmp/synthetic_cache"
)


class CacheTier(Enum):
    """Cache tier levels."""
    L1_MEMORY = "memory"  # In-process memory cache
    L2_REDIS = "redis"    # Distributed Redis cache
    L3_DISK = "disk"      # Disk-based cache for large objects


@dataclass
class CacheEntry:
    """Cache entry with metadata."""
    key: str
    value: Any
    tier: CacheTier
    created_at: datetime
    expires_at: Optional[datetime]
    access_count: int = 0
    last_accessed: Optional[datetime] = None
    size_bytes: int = 0


class CacheManager:
    """Multi-tier cache management system."""
    
    def __init__(self):
        self.l1_cache = lru.LRU(1000)  # In-memory LRU cache
        self.cache_stats = defaultdict(int)
        self._start_background_tasks()
    
    def _start_background_tasks(self):
        """Start background cache maintenance tasks."""
        asyncio.create_task(self._eviction_worker())
        asyncio.create_task(self._warmup_worker())
    
    def _generate_key(self, prefix: str, params: Dict[str, Any]) -> str:
        """Generate cache key from parameters."""
        # Sort params for consistent key generation
        sorted_params = json.dumps(params, sort_keys=True)
        hash_digest = hashlib.md5(sorted_params.encode()).hexdigest()
        return f"{prefix}:{hash_digest}"
    
    async def get(
        self,
        key: str,
        tier: Optional[CacheTier] = None
    ) -> Optional[Any]:
        """Get value from cache."""
        # Try L1 memory cache first
        if key in self.l1_cache:
            self.cache_stats["l1_hits"] += 1
            return self.l1_cache[key]
        
        # Try L2 Redis cache
        try:
            redis_value = await self._get_redis(key)
            if redis_value:
                self.cache_stats["l2_hits"] += 1
                # Promote to L1
                self.l1_cache[key] = redis_value
                return redis_value
        except Exception as e:
            logger.warning(f"Redis cache error: {e}")
        
        # Try L3 disk cache
        if tier != CacheTier.L1_MEMORY:
            try:
                disk_value = await disk_cache.get(key)
                if disk_value:
                    self.cache_stats["l3_hits"] += 1
                    # Promote to higher tiers
                    await self._promote_to_redis(key, disk_value)
                    self.l1_cache[key] = disk_value
                    return disk_value
            except Exception as e:
                logger.warning(f"Disk cache error: {e}")
        
        self.cache_stats["misses"] += 1
        return None
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        tier: CacheTier = CacheTier.L2_REDIS
    ) -> bool:
        """Set value in cache."""
        try:
            # Calculate size
            size_bytes = len(pickle.dumps(value))
            
            # Store in appropriate tier based on size
            if size_bytes < 1024 * 10:  # < 10KB -> Memory
                self.l1_cache[key] = value
                tier = CacheTier.L1_MEMORY
            
            if size_bytes < 1024 * 1024:  # < 1MB -> Redis
                await self._set_redis(key, value, ttl)
                tier = CacheTier.L2_REDIS
            else:  # Large objects -> Disk
                await disk_cache.set(key, value, ttl=ttl)
                tier = CacheTier.L3_DISK
            
            # Track metadata
            entry = CacheEntry(
                key=key,
                value=value,
                tier=tier,
                created_at=datetime.utcnow(),
                expires_at=datetime.utcnow() + timedelta(seconds=ttl) if ttl else None,
                size_bytes=size_bytes
            )
            
            await self._store_metadata(entry)
            self.cache_stats["sets"] += 1
            
            return True
            
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete value from all cache tiers."""
        deleted = False
        
        # Delete from L1
        if key in self.l1_cache:
            del self.l1_cache[key]
            deleted = True
        
        # Delete from L2
        try:
            if redis_master.delete(key):
                deleted = True
        except:
            pass
        
        # Delete from L3
        try:
            if await disk_cache.delete(key):
                deleted = True
        except:
            pass
        
        self.cache_stats["deletes"] += 1
        return deleted
    
    async def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate all keys matching pattern."""
        count = 0
        
        # Clear from L1
        keys_to_delete = [k for k in self.l1_cache.keys() if pattern in k]
        for key in keys_to_delete:
            del self.l1_cache[key]
            count += 1
        
        # Clear from Redis
        try:
            for key in redis_master.scan_iter(match=f"*{pattern}*"):
                redis_master.delete(key)
                count += 1
        except:
            pass
        
        logger.info(f"Invalidated {count} cache entries matching {pattern}")
        return count
    
    async def _get_redis(self, key: str) -> Optional[Any]:
        """Get from Redis with fallback to slave."""
        try:
            # Try master first
            value = redis_master.get(key)
            if value:
                return json.loads(value)
        except:
            # Fallback to slave
            try:
                value = redis_slave.get(key)
                if value:
                    return json.loads(value)
            except:
                pass
        return None
    
    async def _set_redis(self, key: str, value: Any, ttl: Optional[int] = None):
        """Set in Redis with replication."""
        try:
            serialized = json.dumps(value, default=str)
            if ttl:
                redis_master.setex(key, ttl, serialized)
            else:
                redis_master.set(key, serialized)
        except Exception as e:
            logger.error(f"Redis set error: {e}")
    
    async def _promote_to_redis(self, key: str, value: Any):
        """Promote value from disk to Redis cache."""
        try:
            await self._set_redis(key, value, ttl=3600)  # 1 hour TTL for promoted items
        except:
            pass
    
    async def _store_metadata(self, entry: CacheEntry):
        """Store cache entry metadata."""
        try:
            metadata = {
                "tier": entry.tier.value,
                "created_at": entry.created_at.isoformat(),
                "expires_at": entry.expires_at.isoformat() if entry.expires_at else None,
                "size_bytes": entry.size_bytes
            }
            redis_master.hset("cache_metadata", entry.key, json.dumps(metadata))
        except:
            pass
    
    async def _eviction_worker(self):
        """Background worker for cache eviction."""
        while True:
            try:
                # Check memory usage
                if len(self.l1_cache) > 800:  # 80% of capacity
                    # Evict LRU items
                    while len(self.l1_cache) > 600:
                        self.l1_cache.popitem()
                
                # Clean expired Redis keys
                # Redis handles TTL automatically
                
                await asyncio.sleep(60)  # Run every minute
            except Exception as e:
                logger.error(f"Eviction worker error: {e}")
                await asyncio.sleep(60)
    
    async def _warmup_worker(self):
        """Background worker for cache warmup."""
        while True:
            try:
                # Identify frequently accessed keys
                popular_keys = redis_master.zrevrange("popular_keys", 0, 20)
                
                for key in popular_keys:
                    if key not in self.l1_cache:
                        value = await self._get_redis(key)
                        if value:
                            self.l1_cache[key] = value
                
                await asyncio.sleep(300)  # Run every 5 minutes
            except Exception as e:
                logger.error(f"Warmup worker error: {e}")
                await asyncio.sleep(300)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_requests = sum([
            self.cache_stats["l1_hits"],
            self.cache_stats["l2_hits"],
            self.cache_stats["l3_hits"],
            self.cache_stats["misses"]
        ])
        
        hit_rate = 0
        if total_requests > 0:
            total_hits = sum([
                self.cache_stats["l1_hits"],
                self.cache_stats["l2_hits"],
                self.cache_stats["l3_hits"]
            ])
            hit_rate = total_hits / total_requests
        
        return {
            "l1_hits": self.cache_stats["l1_hits"],
            "l2_hits": self.cache_stats["l2_hits"],
            "l3_hits": self.cache_stats["l3_hits"],
            "misses": self.cache_stats["misses"],
            "hit_rate": hit_rate,
            "l1_size": len(self.l1_cache),
            "total_requests": total_requests
        }


class RateLimiter:
    """Distributed rate limiting system."""
    
    def __init__(self):
        self.limits = {}
        self._load_default_limits()
    
    def _load_default_limits(self):
        """Load default rate limits."""
        self.limits = {
            "api_global": {"requests": 10000, "window": 3600},  # 10k/hour global
            "api_per_user": {"requests": 1000, "window": 3600},  # 1k/hour per user
            "api_per_ip": {"requests": 100, "window": 60},  # 100/min per IP
            "generation": {"requests": 100, "window": 3600},  # 100 generations/hour
            "large_generation": {"requests": 10, "window": 3600},  # 10 large/hour
        }
    
    async def check_rate_limit(
        self,
        key: str,
        limit_type: str = "api_per_user",
        custom_limit: Optional[Dict[str, int]] = None
    ) -> Tuple[bool, Dict[str, Any]]:
        """Check if request is within rate limits."""
        
        limit = custom_limit or self.limits.get(limit_type, {})
        if not limit:
            return True, {"allowed": True}
        
        max_requests = limit.get("requests", 100)
        window_seconds = limit.get("window", 60)
        
        # Use sliding window with Redis
        now = time.time()
        window_start = now - window_seconds
        redis_key = f"rate_limit:{limit_type}:{key}"
        
        try:
            # Remove old entries
            redis_master.zremrangebyscore(redis_key, 0, window_start)
            
            # Count current requests
            current_count = redis_master.zcard(redis_key)
            
            if current_count < max_requests:
                # Add current request
                redis_master.zadd(redis_key, {str(now): now})
                redis_master.expire(redis_key, window_seconds)
                
                return True, {
                    "allowed": True,
                    "current": current_count + 1,
                    "limit": max_requests,
                    "resets_in": window_seconds
                }
            else:
                # Rate limit exceeded
                reset_time = redis_master.zrange(redis_key, 0, 0, withscores=True)
                reset_in = window_seconds
                if reset_time:
                    reset_in = int(window_seconds - (now - reset_time[0][1]))
                
                return False, {
                    "allowed": False,
                    "current": current_count,
                    "limit": max_requests,
                    "resets_in": reset_in
                }
                
        except Exception as e:
            logger.error(f"Rate limit check error: {e}")
            # Allow on error (fail open)
            return True, {"allowed": True, "error": str(e)}
    
    async def get_remaining(
        self,
        key: str,
        limit_type: str = "api_per_user"
    ) -> int:
        """Get remaining requests in current window."""
        limit = self.limits.get(limit_type, {})
        max_requests = limit.get("requests", 100)
        window_seconds = limit.get("window", 60)
        
        redis_key = f"rate_limit:{limit_type}:{key}"
        
        try:
            now = time.time()
            window_start = now - window_seconds
            redis_master.zremrangebyscore(redis_key, 0, window_start)
            current_count = redis_master.zcard(redis_key)
            return max(0, max_requests - current_count)
        except:
            return max_requests


class CircuitBreaker:
    """Circuit breaker for fault tolerance."""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type = Exception
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half-open
    
    async def call(self, func: Callable, *args, **kwargs):
        """Execute function with circuit breaker protection."""
        
        # Check if circuit is open
        if self.state == "open":
            if self.last_failure_time:
                time_since_failure = time.time() - self.last_failure_time
                if time_since_failure > self.recovery_timeout:
                    self.state = "half-open"
                else:
                    raise Exception("Circuit breaker is open")
        
        try:
            result = await func(*args, **kwargs)
            
            # Success - reset failure count
            if self.state == "half-open":
                self.state = "closed"
            self.failure_count = 0
            
            return result
            
        except self.expected_exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.failure_count >= self.failure_threshold:
                self.state = "open"
                logger.error(f"Circuit breaker opened after {self.failure_count} failures")
            
            raise e


def cached(
    ttl: int = 3600,
    key_prefix: Optional[str] = None,
    tier: CacheTier = CacheTier.L2_REDIS
):
    """Decorator for caching function results."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key
            cache_manager = CacheManager()
            prefix = key_prefix or func.__name__
            cache_key = cache_manager._generate_key(prefix, kwargs)
            
            # Try to get from cache
            cached_value = await cache_manager.get(cache_key, tier)
            if cached_value is not None:
                logger.debug(f"Cache hit for {cache_key}")
                return cached_value
            
            # Execute function
            result = await func(*args, **kwargs)
            
            # Store in cache
            await cache_manager.set(cache_key, result, ttl, tier)
            
            return result
        
        return wrapper
    return decorator


def rate_limited(
    limit_type: str = "api_per_user",
    key_func: Optional[Callable] = None
):
    """Decorator for rate limiting."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            rate_limiter = RateLimiter()
            
            # Extract rate limit key
            if key_func:
                key = key_func(*args, **kwargs)
            else:
                # Default to first argument as key
                key = str(args[0]) if args else "global"
            
            # Check rate limit
            allowed, info = await rate_limiter.check_rate_limit(key, limit_type)
            
            if not allowed:
                raise Exception(f"Rate limit exceeded. Resets in {info['resets_in']} seconds")
            
            # Execute function
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


# Global instances
cache_manager = CacheManager()
rate_limiter = RateLimiter()