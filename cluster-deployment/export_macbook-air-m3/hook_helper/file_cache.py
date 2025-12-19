#!/usr/bin/env python3
'''
File Content Cache for Claude Code
LRU cache to reduce repeated disk reads
'''

from functools import lru_cache
from pathlib import Path
from typing import Optional
import hashlib
import time

class FileCache:
    def __init__(self, max_size=100, ttl=300):
        self.max_size = max_size
        self.ttl = ttl
        self.cache = {}
        self.access_times = {}
        self.file_hashes = {}

    def _get_file_hash(self, filepath: str) -> str:
        '''Get file modification hash'''
        try:
            stat = Path(filepath).stat()
            return f"{stat.st_mtime}_{stat.st_size}"
        except:
            return ""

    def get(self, filepath: str) -> Optional[str]:
        '''Get cached file content if valid'''
        current_hash = self._get_file_hash(filepath)

        if filepath in self.cache:
            # Check if file was modified
            if self.file_hashes.get(filepath) != current_hash:
                self.invalidate(filepath)
                return None

            # Check TTL
            if time.time() - self.access_times[filepath] > self.ttl:
                self.invalidate(filepath)
                return None

            # Cache hit
            self.access_times[filepath] = time.time()
            return self.cache[filepath]

        return None

    def set(self, filepath: str, content: str):
        '''Cache file content'''
        if len(self.cache) >= self.max_size:
            # Evict oldest entry
            oldest = min(self.access_times.items(), key=lambda x: x[1])[0]
            self.invalidate(oldest)

        self.cache[filepath] = content
        self.access_times[filepath] = time.time()
        self.file_hashes[filepath] = self._get_file_hash(filepath)

    def invalidate(self, filepath: str):
        '''Remove from cache'''
        self.cache.pop(filepath, None)
        self.access_times.pop(filepath, None)
        self.file_hashes.pop(filepath, None)

# Global cache instance
file_cache = FileCache(max_size=100, ttl=300)
