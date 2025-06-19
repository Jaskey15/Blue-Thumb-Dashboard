#!/usr/bin/env python3
"""
Map Cache Management Script

Simple utility script for managing the Blue Thumb map data cache.
Use this script to warm the cache, check status, or clear expired entries.

Usage:
    python manage_cache.py status      # Check cache status
    python manage_cache.py warm        # Warm cache with all map data
    python manage_cache.py clear       # Clear all cache data
"""

import sys
import argparse
from datetime import datetime

def main():
    parser = argparse.ArgumentParser(description='Manage Blue Thumb map data cache')
    parser.add_argument('action', choices=['status', 'warm', 'clear'], 
                       help='Action to perform on the cache')
    
    args = parser.parse_args()
    
    print(f"🗺️  Blue Thumb Map Cache Manager")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Action: {args.action}")
    print("-" * 50)
    
    try:
        if args.action == 'status':
            check_cache_status()
        elif args.action == 'warm':
            warm_cache()
        elif args.action == 'clear':
            clear_cache()
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

def check_cache_status():
    """Check and display cache status information."""
    try:
        from visualizations.cached_map_queries import get_cache_status
        
        print("📊 Checking cache status...")
        status = get_cache_status()
        
        if 'error' in status:
            print(f"❌ Error getting cache status: {status['error']}")
            return
        
        print(f"📦 Total cached items: {status['total_cached_items']}")
        
        if status['cache_types']:
            print("\n📋 Cache by data type:")
            for data_type, count in status['cache_types'].items():
                print(f"   • {data_type}: {count} cached entries")
        else:
            print("📋 No cached data found")
        
        if status['cache_freshness']:
            print("\n⏰ Cache freshness:")
            for key, age in status['cache_freshness'].items():
                print(f"   • {key}: {age}")
        
        print("\n✅ Cache status check complete")
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure you're running this from the project root directory")
    except Exception as e:
        print(f"❌ Error checking cache status: {e}")

def warm_cache():
    """Pre-populate cache with all map data."""
    try:
        from visualizations.cached_map_queries import warm_map_cache
        
        print("🔥 Warming map cache...")
        print("This will fetch fresh data for all map types and cache it.")
        print("Expected time: 5-10 seconds for all data types")
        print()
        
        results = warm_map_cache()
        
        print("\n📊 Cache warming results:")
        total_sites = 0
        success_count = 0
        
        for data_type, result in results.items():
            if result['success']:
                sites = result['sites_cached']
                total_sites += sites
                success_count += 1
                print(f"   ✅ {data_type}: {sites} sites cached")
            else:
                print(f"   ❌ {data_type}: {result['error']}")
        
        print(f"\n🎯 Summary: {success_count}/4 data types cached, {total_sites} total sites")
        
        if success_count == 4:
            print("✅ Cache warming complete! Maps should now load very fast.")
        else:
            print("⚠️  Some data types failed to cache. Check logs for details.")
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure you're running this from the project root directory")
    except Exception as e:
        print(f"❌ Error warming cache: {e}")

def clear_cache():
    """Clear all cached map data."""
    try:
        from cache_utils import clear_all_map_cache
        
        print("🗑️  Clearing all map cache data...")
        
        # Ask for confirmation
        confirm = input("Are you sure you want to clear all cached map data? (y/N): ")
        if confirm.lower() != 'y':
            print("❌ Cache clear cancelled")
            return
        
        success = clear_all_map_cache()
        
        if success:
            print("✅ All map cache data cleared successfully")
            print("Next map load will fetch fresh data from database")
        else:
            print("❌ Error clearing cache data")
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure you're running this from the project root directory")
    except Exception as e:
        print(f"❌ Error clearing cache: {e}")

if __name__ == "__main__":
    main() 