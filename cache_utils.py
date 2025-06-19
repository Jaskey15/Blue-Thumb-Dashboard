"""
Cache utility functions for the Blue Thumb Dashboard.
Provides caching functionality to improve dashboard performance.
"""

import os
import pickle
from datetime import datetime
from utils import setup_logging

# Initialize logger for cache operations
logger = setup_logging("cache_utils")

# Cache configuration constants
CACHE_EXPIRATION_HOURS = 1
CACHE_DIR = "cache"

# Ensure cache directory exists
if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)

# ============================================================================
# CACHE UTILITY FUNCTIONS 
# ============================================================================

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

# ============================================================================
# MAP-SPECIFIC CACHE FUNCTIONS
# ============================================================================

def get_map_cache_key(data_type, site_name=None):
    """
    Generate cache keys specifically for map data.
    
    Args:
        data_type: Type of map data ('chemical', 'fish', 'macro', 'habitat', 'sites')
        site_name: Optional site name for site-specific caching
    
    Returns:
        str: Map-specific cache key
    """
    if site_name:
        return f"map_{data_type}_{site_name}"
    return f"map_{data_type}_all"

def get_map_cache_file_path(cache_key):
    """
    Get the file path for a map cache key.
    
    Args:
        cache_key: Cache key for map data
    
    Returns:
        str: Full file path for the cache file
    """
    return os.path.join(CACHE_DIR, f"{cache_key}.pkl")

def load_map_cache():
    """
    Load the entire map cache from disk.
    
    Returns:
        dict: Map cache data or empty dict if no cache exists
    """
    try:
        cache_file = os.path.join(CACHE_DIR, "map_cache.pkl")
        if os.path.exists(cache_file):
            with open(cache_file, 'rb') as f:
                cache_data = pickle.load(f)
            logger.info("Loaded map cache from disk")
            return cache_data
        else:
            logger.info("No existing map cache found, starting fresh")
            return {}
    except Exception as e:
        logger.error(f"Error loading map cache: {e}")
        return {}

def save_map_cache(cache_data):
    """
    Save the entire map cache to disk.
    
    Args:
        cache_data: Dictionary containing cache data
    
    Returns:
        bool: True if save successful, False otherwise
    """
    try:
        cache_file = os.path.join(CACHE_DIR, "map_cache.pkl")
        with open(cache_file, 'wb') as f:
            pickle.dump(cache_data, f)
        logger.info("Saved map cache to disk")
        return True
    except Exception as e:
        logger.error(f"Error saving map cache: {e}")
        return False

def get_cached_map_data(data_type, site_name=None):
    """
    Retrieve cached map data if valid.
    
    Args:
        data_type: Type of map data ('chemical', 'fish', 'macro', 'habitat', 'sites')
        site_name: Optional site name for site-specific data
    
    Returns:
        DataFrame or list or None if no valid cache exists
    """
    try:
        # Load cache from disk
        cache_store = load_map_cache()
        
        # Clean expired entries
        cache_store = clear_expired_cache(cache_store)
        
        # Get cache key and check for data
        cache_key = get_map_cache_key(data_type, site_name)
        cached_data = get_cached_data(cache_store, cache_key)
        
        if cached_data is not None:
            logger.info(f"Retrieved cached map data for: {cache_key}")
            
        return cached_data
    except Exception as e:
        logger.error(f"Error retrieving cached map data: {e}")
        return None

def set_cached_map_data(data_type, data, site_name=None):
    """
    Cache map data to disk.
    
    Args:
        data_type: Type of map data ('chemical', 'fish', 'macro', 'habitat', 'sites')
        data: DataFrame or list to cache
        site_name: Optional site name for site-specific data
    
    Returns:
        bool: True if caching successful, False otherwise
    """
    try:
        # Load existing cache
        cache_store = load_map_cache()
        
        # Clean expired entries
        cache_store = clear_expired_cache(cache_store)
        
        # Add new data to cache
        cache_key = get_map_cache_key(data_type, site_name)
        cache_store = set_cache_data(cache_store, cache_key, data)
        
        # Save back to disk
        success = save_map_cache(cache_store)
        
        if success:
            logger.info(f"Successfully cached map data for: {cache_key}")
        
        return success
    except Exception as e:
        logger.error(f"Error caching map data: {e}")
        return False

def get_cached_sites():
    """
    Retrieve cached site metadata if valid.
    
    Returns:
        List of site dictionaries or None if no valid cache exists
    """
    return get_cached_map_data('sites')

def set_cached_sites(sites_data):
    """
    Cache site metadata.
    
    Args:
        sites_data: List of site dictionaries to cache
    
    Returns:
        bool: True if caching successful, False otherwise
    """
    return set_cached_map_data('sites', sites_data)

def clear_all_map_cache():
    """
    Clear all cached map data including sites.
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        cache_file = os.path.join(CACHE_DIR, "map_cache.pkl")
        if os.path.exists(cache_file):
            os.remove(cache_file)
            logger.info("Cleared all map cache data")
        
        # Also clear individual cache files if they exist
        for data_type in ['chemical', 'fish', 'macro', 'habitat', 'sites']:
            cache_key = get_map_cache_key(data_type)
            cache_file_path = get_map_cache_file_path(cache_key)
            if os.path.exists(cache_file_path):
                os.remove(cache_file_path)
                
        return True
    except Exception as e:
        logger.error(f"Error clearing map cache: {e}")
        return False