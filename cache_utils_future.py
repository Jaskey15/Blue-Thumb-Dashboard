"""
Cache utility functions for the Tenmile Creek Water Quality Dashboard.
Provides caching functionality to improve dashboard performance.
"""

from utils import setup_logging

# Initialize logger for cache operations
logger = setup_logging("cache_utils")

# Cache configuration constants
CACHE_EXPIRATION_HOURS = 1

# Cache utility functions
def get_cache_key(param_type, param_name, season=None):
    """
    Generate a structured cache key.
    
    Args:
        param_type: Type of parameter ('chemical', 'bio', 'habitat')
        param_name: Specific parameter name (e.g., 'do_percent', 'Fish_IBI')
        season: Optional season for biological data ('Summer', 'Winter')
    
    Returns:
        str: Structured cache key like 'chemical:do_percent' or 'bio:Macro_Summer'
    """
    if season:
        return f"{param_type}:{param_name}_{season}"
    return f"{param_type}:{param_name}"

def is_expired(timestamp):
    """
    Check if a timestamp is older than the cache expiration time.
    
    Args:
        timestamp: ISO format timestamp string
    
    Returns:
        bool: True if expired, False if still valid
    """
    try:
        import pandas as pd
        from datetime import datetime, timedelta
        
        cache_time = pd.to_datetime(timestamp)
        now = datetime.now()
        expiration_time = cache_time + timedelta(hours=CACHE_EXPIRATION_HOURS)
        
        return now > expiration_time
    except Exception as e:
        logger.error(f"Error checking timestamp expiration: {e}")
        return True  # Assume expired if we can't parse

def is_cache_valid(cache_store, key):
    """
    Check if cached data exists and is not expired.
    
    Args:
        cache_store: Dict containing cached data
        key: Cache key to check
    
    Returns:
        bool: True if valid cached data exists, False otherwise
    """
    try:
        if not cache_store or key not in cache_store:
            logger.info(f"Cache MISS - No data found for key: {key}")
            return False
        
        cache_entry = cache_store[key]
        if 'timestamp' not in cache_entry or 'data' not in cache_entry:
            logger.warning(f"Cache MISS - Invalid cache entry structure for key: {key}")
            return False
        
        if is_expired(cache_entry['timestamp']):
            logger.info(f"Cache MISS - Expired data for key: {key}")
            return False
        
        logger.info(f"Cache HIT for key: {key}")
        return True
    except Exception as e:
        logger.error(f"Error validating cache for key {key}: {e}")
        return False

def get_cached_data(cache_store, key):
    """
    Retrieve cached data if valid.
    
    Args:
        cache_store: Dict containing cached data
        key: Cache key to retrieve
    
    Returns:
        Data from cache or None if invalid/missing
    """
    try:
        if is_cache_valid(cache_store, key):
            return cache_store[key]['data']
        return None
    except Exception as e:
        logger.error(f"Error retrieving cached data for key {key}: {e}")
        return None

def set_cache_data(cache_store, key, data):
    """
    Store data in cache with timestamp.
    
    Args:
        cache_store: Dict to store cached data in
        key: Cache key
        data: Data to cache
    
    Returns:
        Updated cache_store dict
    """
    try:
        from datetime import datetime
        
        if cache_store is None:
            cache_store = {}
        
        cache_store[key] = {
            'data': data,
            'timestamp': datetime.now().isoformat(),
        }
        
        logger.info(f"Cached fresh data for key: {key}")
        return cache_store
    except Exception as e:
        logger.error(f"Error caching data for key {key}: {e}")
        return cache_store or {}

def clear_expired_cache(cache_store):
    """
    Remove expired entries from cache store.
    
    Args:
        cache_store: Dict containing cached data
    
    Returns:
        Cleaned cache_store dict
    """
    try:
        if not cache_store:
            return {}
        
        # Get list of keys to avoid modifying dict during iteration
        keys_to_check = list(cache_store.keys())
        expired_keys = []
        
        for key in keys_to_check:
            cache_entry = cache_store.get(key, {})
            if 'timestamp' in cache_entry:
                if is_expired(cache_entry['timestamp']):
                    expired_keys.append(key)
        
        # Remove expired keys
        for key in expired_keys:
            del cache_store[key]
            logger.info(f"Removed expired cache entry: {key}")
        
        if expired_keys:
            logger.info(f"Cleaned {len(expired_keys)} expired cache entries")
        
        return cache_store
    except Exception as e:
        logger.error(f"Error cleaning expired cache: {e}")
        return cache_store or {}