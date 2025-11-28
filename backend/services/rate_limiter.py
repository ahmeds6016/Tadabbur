"""
Redis-based Rate Limiter using sliding window algorithm
Provides distributed rate limiting across multiple instances
"""

import time
import logging
from typing import Optional, Tuple
import redis
from redis.exceptions import RedisError, ConnectionError as RedisConnectionError
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class RateLimiter:
    """Redis-based rate limiter with sliding window algorithm"""

    def __init__(self, redis_client: redis.Redis):
        """
        Initialize rate limiter with Redis client

        Args:
            redis_client: Redis client instance
        """
        self.redis_client = redis_client

        # Default limits (can be overridden per user tier)
        self.DEFAULT_LIMITS = {
            'requests_per_minute': 30,
            'requests_per_hour': 500,
            'requests_per_day': 2000
        }

        # User tier limits
        self.TIER_LIMITS = {
            'free': {
                'requests_per_minute': 20,
                'requests_per_hour': 300,
                'requests_per_day': 1000
            },
            'premium': {
                'requests_per_minute': 60,
                'requests_per_hour': 1000,
                'requests_per_day': 5000
            },
            'unlimited': {
                'requests_per_minute': 1000,
                'requests_per_hour': 10000,
                'requests_per_day': 100000
            }
        }

    def _get_window_key(self, identifier: str, window: str) -> str:
        """
        Generate Redis key for rate limit window

        Args:
            identifier: User ID or IP address
            window: Time window (minute/hour/day)

        Returns:
            Redis key string
        """
        return f"rate_limit:{identifier}:{window}"

    def _get_current_windows(self) -> dict:
        """
        Get current time windows

        Returns:
            Dict with current minute, hour, and day keys
        """
        now = datetime.utcnow()
        return {
            'minute': now.strftime('%Y%m%d%H%M'),
            'hour': now.strftime('%Y%m%d%H'),
            'day': now.strftime('%Y%m%d')
        }

    def check_rate_limit(self, identifier: str, tier: str = 'free') -> Tuple[bool, Optional[dict]]:
        """
        Check if request is within rate limits using sliding window

        Args:
            identifier: User ID or IP address
            tier: User tier (free/premium/unlimited)

        Returns:
            Tuple of (is_allowed, limit_info)
        """
        try:
            # Get limits for tier
            limits = self.TIER_LIMITS.get(tier, self.DEFAULT_LIMITS)
            current_windows = self._get_current_windows()
            current_timestamp = time.time()

            # Use Redis pipeline for atomic operations
            pipe = self.redis_client.pipeline()

            # Check each window
            for window_type, window_key in current_windows.items():
                redis_key = f"rate_limit:{identifier}:{window_type}:{window_key}"

                # Remove old entries from sliding window
                if window_type == 'minute':
                    window_start = current_timestamp - 60
                elif window_type == 'hour':
                    window_start = current_timestamp - 3600
                else:  # day
                    window_start = current_timestamp - 86400

                # Remove old entries and count current
                pipe.zremrangebyscore(redis_key, 0, window_start)
                pipe.zcard(redis_key)

            results = pipe.execute()

            # Check limits (results are in pairs: remove result, count)
            limit_info = {
                'minute': {
                    'used': results[1],
                    'limit': limits['requests_per_minute'],
                    'remaining': max(0, limits['requests_per_minute'] - results[1])
                },
                'hour': {
                    'used': results[3],
                    'limit': limits['requests_per_hour'],
                    'remaining': max(0, limits['requests_per_hour'] - results[3])
                },
                'day': {
                    'used': results[5],
                    'limit': limits['requests_per_day'],
                    'remaining': max(0, limits['requests_per_day'] - results[5])
                }
            }

            # Check if any limit is exceeded
            for window_type in ['minute', 'hour', 'day']:
                if limit_info[window_type]['used'] >= limit_info[window_type]['limit']:
                    logger.warning(f"Rate limit exceeded for {identifier} on {window_type} window")
                    limit_info['exceeded'] = window_type
                    limit_info['retry_after'] = self._calculate_retry_after(window_type)
                    return False, limit_info

            # If within limits, add current request to all windows
            pipe = self.redis_client.pipeline()
            for window_type, window_key in current_windows.items():
                redis_key = f"rate_limit:{identifier}:{window_type}:{window_key}"
                pipe.zadd(redis_key, {str(current_timestamp): current_timestamp})

                # Set expiry
                if window_type == 'minute':
                    pipe.expire(redis_key, 60)
                elif window_type == 'hour':
                    pipe.expire(redis_key, 3600)
                else:  # day
                    pipe.expire(redis_key, 86400)

            pipe.execute()

            return True, limit_info

        except (RedisError, RedisConnectionError) as e:
            logger.error(f"Redis error in rate limiter: {e}")
            # On Redis failure, allow request but log warning
            return True, None
        except Exception as e:
            logger.error(f"Unexpected error in rate limiter: {e}")
            return True, None

    def _calculate_retry_after(self, window_type: str) -> int:
        """
        Calculate seconds until rate limit resets

        Args:
            window_type: Type of window that was exceeded

        Returns:
            Seconds until reset
        """
        now = datetime.utcnow()

        if window_type == 'minute':
            next_window = now.replace(second=0, microsecond=0) + timedelta(minutes=1)
        elif window_type == 'hour':
            next_window = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
        else:  # day
            next_window = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)

        return int((next_window - now).total_seconds())

    def reset_limits(self, identifier: str):
        """
        Reset rate limits for an identifier (admin function)

        Args:
            identifier: User ID or IP to reset
        """
        try:
            pattern = f"rate_limit:{identifier}:*"
            keys = self.redis_client.keys(pattern)

            if keys:
                self.redis_client.delete(*keys)
                logger.info(f"Reset rate limits for {identifier}")

        except (RedisError, RedisConnectionError) as e:
            logger.error(f"Failed to reset rate limits: {e}")

    def get_usage_stats(self, identifier: str, tier: str = 'free') -> dict:
        """
        Get current usage statistics for an identifier

        Args:
            identifier: User ID or IP address
            tier: User tier

        Returns:
            Usage statistics dictionary
        """
        try:
            limits = self.TIER_LIMITS.get(tier, self.DEFAULT_LIMITS)
            current_windows = self._get_current_windows()
            current_timestamp = time.time()

            stats = {}

            for window_type, window_key in current_windows.items():
                redis_key = f"rate_limit:{identifier}:{window_type}:{window_key}"

                # Get count for window
                if window_type == 'minute':
                    window_start = current_timestamp - 60
                elif window_type == 'hour':
                    window_start = current_timestamp - 3600
                else:  # day
                    window_start = current_timestamp - 86400

                count = self.redis_client.zcount(redis_key, window_start, current_timestamp)

                stats[window_type] = {
                    'used': count,
                    'limit': limits[f'requests_per_{window_type}'],
                    'remaining': max(0, limits[f'requests_per_{window_type}'] - count),
                    'percentage': round((count / limits[f'requests_per_{window_type}']) * 100, 2)
                }

            return stats

        except (RedisError, RedisConnectionError) as e:
            logger.error(f"Failed to get usage stats: {e}")
            return {}

    def set_custom_limits(self, identifier: str, custom_limits: dict):
        """
        Set custom rate limits for a specific identifier

        Args:
            identifier: User ID to set custom limits for
            custom_limits: Dictionary with custom limits
        """
        try:
            key = f"rate_limit:custom:{identifier}"
            self.redis_client.hset(key, mapping=custom_limits)
            self.redis_client.expire(key, 86400 * 30)  # 30 days expiry
            logger.info(f"Set custom limits for {identifier}: {custom_limits}")

        except (RedisError, RedisConnectionError) as e:
            logger.error(f"Failed to set custom limits: {e}")

    def get_custom_limits(self, identifier: str) -> Optional[dict]:
        """
        Get custom limits for an identifier if they exist

        Args:
            identifier: User ID to check

        Returns:
            Custom limits dictionary or None
        """
        try:
            key = f"rate_limit:custom:{identifier}"
            custom = self.redis_client.hgetall(key)

            if custom:
                return {k.decode(): int(v.decode()) for k, v in custom.items()}

            return None

        except (RedisError, RedisConnectionError) as e:
            logger.error(f"Failed to get custom limits: {e}")
            return None


class IPRateLimiter(RateLimiter):
    """IP-based rate limiter for unauthenticated requests"""

    def __init__(self, redis_client: redis.Redis):
        """Initialize IP rate limiter with stricter limits"""
        super().__init__(redis_client)

        # Stricter limits for IP-based limiting
        self.DEFAULT_LIMITS = {
            'requests_per_minute': 10,
            'requests_per_hour': 100,
            'requests_per_day': 500
        }

        self.TIER_LIMITS = {
            'anonymous': {
                'requests_per_minute': 10,
                'requests_per_hour': 100,
                'requests_per_day': 500
            }
        }

    def check_ip_limit(self, ip_address: str) -> Tuple[bool, Optional[dict]]:
        """
        Check rate limit for IP address

        Args:
            ip_address: IP address to check

        Returns:
            Tuple of (is_allowed, limit_info)
        """
        return self.check_rate_limit(f"ip:{ip_address}", 'anonymous')