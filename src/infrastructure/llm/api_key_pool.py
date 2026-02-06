"""API Key Pool for load balancing across multiple OpenAI API keys."""
import asyncio
import time
from typing import List, Optional, Dict
from collections import defaultdict
from datetime import datetime, timedelta


class APIKeyPool:
    """
    Round-robin pool of API keys for load balancing.
    
    Features:
    - Round-robin key selection
    - Per-key rate limit tracking
    - Automatic key rotation on errors
    - Usage statistics
    """
    
    def __init__(
        self,
        api_keys: List[str],
        rate_limit_rpm: int = 500,
        track_usage: bool = True
    ):
        """
        Initialize API key pool.
        
        Args:
            api_keys: List of OpenAI API keys
            rate_limit_rpm: Requests per minute limit per key
            track_usage: Whether to track per-key usage statistics
        """
        if not api_keys:
            raise ValueError("At least one API key is required")
        
        self.api_keys = api_keys
        self.rate_limit_rpm = rate_limit_rpm
        self.track_usage = track_usage
        
        self.index = 0
        self.lock = asyncio.Lock()
        
        # Per-key statistics
        self.usage_stats: Dict[str, Dict] = {
            key: {
                "requests": 0,
                "errors": 0,
                "rate_limits": 0,
                "last_used": None,
                "request_times": []  # For rate limit tracking
            }
            for key in api_keys
        }
    
    async def get_next_key(self) -> str:
        """
        Get next API key in round-robin fashion.
        
        Returns:
            API key string
        """
        async with self.lock:
            key = self.api_keys[self.index]
            self.index = (self.index + 1) % len(self.api_keys)
            
            if self.track_usage:
                self.usage_stats[key]["last_used"] = datetime.now()
                self.usage_stats[key]["requests"] += 1
                
                # Track request time for rate limiting
                now = time.time()
                self.usage_stats[key]["request_times"].append(now)
                
                # Clean old request times (older than 1 minute)
                cutoff = now - 60
                self.usage_stats[key]["request_times"] = [
                    t for t in self.usage_stats[key]["request_times"]
                    if t > cutoff
                ]
            
            return key
    
    async def get_key_with_capacity(self) -> Optional[str]:
        """
        Get a key that has capacity (not hitting rate limit).
        
        Returns:
            API key or None if all keys are at capacity
        """
        async with self.lock:
            now = time.time()
            cutoff = now - 60
            
            # Find key with lowest recent usage
            best_key = None
            min_requests = float('inf')
            
            for key in self.api_keys:
                # Count recent requests
                recent_requests = sum(
                    1 for t in self.usage_stats[key]["request_times"]
                    if t > cutoff
                )
                
                if recent_requests < self.rate_limit_rpm and recent_requests < min_requests:
                    best_key = key
                    min_requests = recent_requests
            
            if best_key:
                self.usage_stats[best_key]["last_used"] = datetime.now()
                self.usage_stats[best_key]["requests"] += 1
                self.usage_stats[best_key]["request_times"].append(now)
            
            return best_key
    
    async def record_error(self, api_key: str, is_rate_limit: bool = False):
        """
        Record an error for a specific API key.
        
        Args:
            api_key: The API key that encountered an error
            is_rate_limit: Whether the error was a rate limit error
        """
        async with self.lock:
            if api_key in self.usage_stats:
                self.usage_stats[api_key]["errors"] += 1
                if is_rate_limit:
                    self.usage_stats[api_key]["rate_limits"] += 1
    
    def get_stats(self) -> Dict[str, Dict]:
        """
        Get usage statistics for all keys.
        
        Returns:
            Dictionary mapping key (last 4 chars) to stats
        """
        return {
            f"...{key[-4:]}": {
                "requests": stats["requests"],
                "errors": stats["errors"],
                "rate_limits": stats["rate_limits"],
                "last_used": stats["last_used"].isoformat() if stats["last_used"] else None,
                "recent_rpm": sum(
                    1 for t in stats["request_times"]
                    if t > time.time() - 60
                )
            }
            for key, stats in self.usage_stats.items()
        }
    
    def print_stats(self):
        """Print usage statistics in a formatted table."""
        stats = self.get_stats()
        
        print("\n" + "="*80)
        print("API KEY POOL STATISTICS")
        print("="*80)
        print(f"{'Key':<15} {'Requests':>10} {'Errors':>10} {'Rate Limits':>12} {'Recent RPM':>12}")
        print("-"*80)
        
        for key_suffix, stat in stats.items():
            print(f"{key_suffix:<15} {stat['requests']:>10} {stat['errors']:>10} "
                  f"{stat['rate_limits']:>12} {stat['recent_rpm']:>12}")
        
        print("="*80)
        print(f"Total API keys: {len(self.api_keys)}")
        print(f"Rate limit per key: {self.rate_limit_rpm} RPM")
        print(f"Total capacity: {self.rate_limit_rpm * len(self.api_keys)} RPM")
        print("="*80)
    
    def __len__(self) -> int:
        """Return number of API keys in pool."""
        return len(self.api_keys)
    
    @classmethod
    def from_env_string(cls, env_string: str, **kwargs) -> 'APIKeyPool':
        """
        Create pool from comma-separated environment variable string.
        
        Args:
            env_string: Comma-separated API keys
            **kwargs: Additional arguments for APIKeyPool
            
        Returns:
            APIKeyPool instance
        """
        keys = [k.strip() for k in env_string.split(',') if k.strip()]
        return cls(keys, **kwargs)
