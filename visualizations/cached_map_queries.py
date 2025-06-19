"""
Cached wrapper functions for map visualization queries.

This module provides caching functionality for map data queries to dramatically
improve performance. Functions check cache first, then fall back to the existing
optimized database queries if no valid cache exists.

Cache Strategy:
- 1-hour expiration for all map data
- Shared cache across all users for maximum efficiency
- Automatic fallback to database queries if caching fails
- File-based persistent cache storage

Functions:
- get_latest_chemical_data_for_maps_cached(): Cached chemical data
- get_latest_fish_data_for_maps_cached(): Cached fish data  
- get_latest_macro_data_for_maps_cached(): Cached macro data
- get_latest_habitat_data_for_maps_cached(): Cached habitat data
"""

import pandas as pd
from utils import setup_logging
from cache_utils import get_cached_map_data, set_cached_map_data

# Import the original optimized functions as fallbacks
from visualizations.map_queries import (
    get_latest_chemical_data_for_maps,
    get_latest_fish_data_for_maps,
    get_latest_macro_data_for_maps,
    get_latest_habitat_data_for_maps
)

# Set up logging
logger = setup_logging("cached_map_queries", category="visualization")

def get_latest_chemical_data_for_maps_cached(site_name=None):
    """
    Get latest chemical data with caching support.
    
    Args:
        site_name: Optional site name to filter data for
        
    Returns:
        DataFrame with latest chemical data per site including status columns
        
    Performance:
        - Cache hit: ~0.05-0.1 seconds
        - Cache miss: ~0.2-0.5 seconds (same as optimized query)
    """
    try:
        # Check cache first
        cached_data = get_cached_map_data('chemical', site_name)
        if cached_data is not None:
            logger.info(f"Cache HIT: Retrieved chemical data from cache (sites: {len(cached_data)})")
            return cached_data
        
        # Cache miss - fetch from database using optimized query
        logger.info("Cache MISS: Fetching fresh chemical data from database")
        data = get_latest_chemical_data_for_maps(site_name)
        
        # Cache the results for future requests (only if we got data)
        if not data.empty:
            success = set_cached_map_data('chemical', data, site_name)
            if success:
                logger.info(f"Successfully cached chemical data (sites: {len(data)})")
            else:
                logger.warning("Failed to cache chemical data, but returning fresh data")
        
        return data
        
    except Exception as e:
        logger.error(f"Error in cached chemical data retrieval: {e}")
        # Fallback to direct database query
        logger.info("Falling back to direct database query")
        return get_latest_chemical_data_for_maps(site_name)

def get_latest_fish_data_for_maps_cached(site_name=None):
    """
    Get latest fish data with caching support.
    
    Args:
        site_name: Optional site name to filter data for
    
    Returns:
        DataFrame with latest fish data per site
        
    Performance:
        - Cache hit: ~0.05-0.1 seconds
        - Cache miss: ~0.2-0.5 seconds (same as optimized query)
    """
    try:
        # Check cache first
        cached_data = get_cached_map_data('fish', site_name)
        if cached_data is not None:
            logger.info(f"Cache HIT: Retrieved fish data from cache (sites: {len(cached_data)})")
            return cached_data
        
        # Cache miss - fetch from database using optimized query
        logger.info("Cache MISS: Fetching fresh fish data from database")
        data = get_latest_fish_data_for_maps(site_name)
        
        # Cache the results for future requests (only if we got data)
        if not data.empty:
            success = set_cached_map_data('fish', data, site_name)
            if success:
                logger.info(f"Successfully cached fish data (sites: {len(data)})")
            else:
                logger.warning("Failed to cache fish data, but returning fresh data")
        
        return data
        
    except Exception as e:
        logger.error(f"Error in cached fish data retrieval: {e}")
        # Fallback to direct database query
        logger.info("Falling back to direct database query")
        return get_latest_fish_data_for_maps(site_name)

def get_latest_macro_data_for_maps_cached(site_name=None):
    """
    Get latest macroinvertebrate data with caching support.
    
    Args:
        site_name: Optional site name to filter data for
    
    Returns:
        DataFrame with latest macro data per site
        
    Performance:
        - Cache hit: ~0.05-0.1 seconds
        - Cache miss: ~0.2-0.5 seconds (same as optimized query)
    """
    try:
        # Check cache first
        cached_data = get_cached_map_data('macro', site_name)
        if cached_data is not None:
            logger.info(f"Cache HIT: Retrieved macro data from cache (sites: {len(cached_data)})")
            return cached_data
        
        # Cache miss - fetch from database using optimized query
        logger.info("Cache MISS: Fetching fresh macro data from database")
        data = get_latest_macro_data_for_maps(site_name)
        
        # Cache the results for future requests (only if we got data)
        if not data.empty:
            success = set_cached_map_data('macro', data, site_name)
            if success:
                logger.info(f"Successfully cached macro data (sites: {len(data)})")
            else:
                logger.warning("Failed to cache macro data, but returning fresh data")
        
        return data
        
    except Exception as e:
        logger.error(f"Error in cached macro data retrieval: {e}")
        # Fallback to direct database query
        logger.info("Falling back to direct database query")
        return get_latest_macro_data_for_maps(site_name)

def get_latest_habitat_data_for_maps_cached(site_name=None):
    """
    Get latest habitat data with caching support.
    
    Args:
        site_name: Optional site name to filter data for
    
    Returns:
        DataFrame with latest habitat data per site
        
    Performance:
        - Cache hit: ~0.05-0.1 seconds
        - Cache miss: ~0.2-0.5 seconds (same as optimized query)
    """
    try:
        # Check cache first
        cached_data = get_cached_map_data('habitat', site_name)
        if cached_data is not None:
            logger.info(f"Cache HIT: Retrieved habitat data from cache (sites: {len(cached_data)})")
            return cached_data
        
        # Cache miss - fetch from database using optimized query
        logger.info("Cache MISS: Fetching fresh habitat data from database")
        data = get_latest_habitat_data_for_maps(site_name)
        
        # Cache the results for future requests (only if we got data)
        if not data.empty:
            success = set_cached_map_data('habitat', data, site_name)
            if success:
                logger.info(f"Successfully cached habitat data (sites: {len(data)})")
            else:
                logger.warning("Failed to cache habitat data, but returning fresh data")
        
        return data
        
    except Exception as e:
        logger.error(f"Error in cached habitat data retrieval: {e}")
        # Fallback to direct database query
        logger.info("Falling back to direct database query")
        return get_latest_habitat_data_for_maps(site_name)

def load_sites_from_database_cached():
    """
    Get site metadata with caching support.
    
    Returns:
        List of site dictionaries with name, lat, lon, county, river_basin, ecoregion, active
        
    Performance:
        - Cache hit: ~0.001-0.005 seconds
        - Cache miss: ~0.1-0.2 seconds (same as database query)
    """
    try:
        from cache_utils import get_cached_sites, set_cached_sites
        
        # Check cache first
        cached_sites = get_cached_sites()
        if cached_sites is not None:
            logger.info(f"Cache HIT: Retrieved site metadata from cache (sites: {len(cached_sites)})")
            return cached_sites
        
        # Cache miss - fetch from database
        logger.info("Cache MISS: Fetching fresh site metadata from database")
        from visualizations.map_viz import load_sites_from_database
        sites = load_sites_from_database()
        
        # Cache the results for future requests (only if we got data)
        if sites:
            success = set_cached_sites(sites)
            if success:
                logger.info(f"Successfully cached site metadata (sites: {len(sites)})")
            else:
                logger.warning("Failed to cache site metadata, but returning fresh data")
        
        return sites
        
    except Exception as e:
        logger.error(f"Error in cached site metadata retrieval: {e}")
        # Fallback to direct database query
        logger.info("Falling back to direct database query")
        from visualizations.map_viz import load_sites_from_database
        return load_sites_from_database()

# ============================================================================
# CACHE MANAGEMENT FUNCTIONS
# ============================================================================

def warm_map_cache():
    """
    Pre-populate cache with all map data types and site metadata.
    
    This function can be called during app startup or manually to ensure
    fast performance for the first user who accesses maps.
    
    Returns:
        dict: Summary of cache warming results
    """
    results = {}
    data_types = ['sites', 'chemical', 'fish', 'macro', 'habitat']
    
    logger.info("Starting map cache warming...")
    
    for data_type in data_types:
        try:
            if data_type == 'sites':
                data = load_sites_from_database_cached()
                results[data_type] = {
                    'success': True,
                    'sites_cached': len(data) if data else 0
                }
                logger.info(f"Cache warmed for {data_type}: {len(data)} sites")
            elif data_type == 'chemical':
                data = get_latest_chemical_data_for_maps_cached()
                results[data_type] = {
                    'success': True,
                    'sites_cached': len(data) if not data.empty else 0
                }
                logger.info(f"Cache warmed for {data_type}: {len(data)} sites")
            elif data_type == 'fish':
                data = get_latest_fish_data_for_maps_cached()
                results[data_type] = {
                    'success': True,
                    'sites_cached': len(data) if not data.empty else 0
                }
                logger.info(f"Cache warmed for {data_type}: {len(data)} sites")
            elif data_type == 'macro':
                data = get_latest_macro_data_for_maps_cached()
                results[data_type] = {
                    'success': True,
                    'sites_cached': len(data) if not data.empty else 0
                }
                logger.info(f"Cache warmed for {data_type}: {len(data)} sites")
            elif data_type == 'habitat':
                data = get_latest_habitat_data_for_maps_cached()
                results[data_type] = {
                    'success': True,
                    'sites_cached': len(data) if not data.empty else 0
                }
                logger.info(f"Cache warmed for {data_type}: {len(data)} sites")
            
        except Exception as e:
            results[data_type] = {
                'success': False,
                'error': str(e)
            }
            logger.error(f"Failed to warm cache for {data_type}: {e}")
    
    total_success = sum(1 for r in results.values() if r['success'])
    logger.info(f"Cache warming completed: {total_success}/{len(data_types)} data types cached")
    
    return results

def get_cache_status():
    """
    Get status information about the current map cache.
    
    Returns:
        dict: Cache status information including hit/miss ratios, sizes, etc.
    """
    try:
        from cache_utils import load_map_cache, clear_expired_cache
        
        # Load and clean cache
        cache_store = load_map_cache()
        cache_store = clear_expired_cache(cache_store)
        
        status = {
            'total_cached_items': len(cache_store),
            'cache_types': {},
            'cache_freshness': {}
        }
        
        # Analyze cache by data type
        for key, entry in cache_store.items():
            if key.startswith('map_'):
                data_type = key.split('_')[1]
                if data_type not in status['cache_types']:
                    status['cache_types'][data_type] = 0
                status['cache_types'][data_type] += 1
                
                # Get cache age
                try:
                    from datetime import datetime
                    import pandas as pd
                    cache_time = pd.to_datetime(entry['timestamp'])
                    age_minutes = (datetime.now() - cache_time).total_seconds() / 60
                    status['cache_freshness'][key] = f"{age_minutes:.1f} minutes old"
                except Exception as e:
                    status['cache_freshness'][key] = "Unknown age"
        
        return status
        
    except Exception as e:
        logger.error(f"Error getting cache status: {e}")
        return {'error': str(e)} 