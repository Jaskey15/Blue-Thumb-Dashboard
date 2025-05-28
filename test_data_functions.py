from utils import get_sites_with_data

def test_site_data_functions():
    """Test the get_sites_with_data function for fish and macro data."""
    
    print("Testing site data functions...")
    print("-" * 50)
    
    # Test fish data
    print("\n1. Testing Fish Data:")
    try:
        fish_sites = get_sites_with_data('fish')
        print(f"   Fish sites found: {len(fish_sites)}")
        print(f"   Expected: ~184 sites")
        
        if fish_sites:
            print(f"   First 5 fish sites: {fish_sites[:5]}")
        else:
            print("   ⚠️  No fish sites returned!")
            
    except Exception as e:
        print(f"   ❌ Error getting fish sites: {e}")
    
    # Test macro data
    print("\n2. Testing Macro Data:")
    try:
        macro_sites = get_sites_with_data('macro')
        print(f"   Macro sites found: {len(macro_sites)}")
        print(f"   Expected: 285+ sites")
        
        if macro_sites:
            print(f"   First 5 macro sites: {macro_sites[:5]}")
        else:
            print("   ⚠️  No macro sites returned!")
            
    except Exception as e:
        print(f"   ❌ Error getting macro sites: {e}")
    
    # Check for overlap (sites with both types)
    if 'fish_sites' in locals() and 'macro_sites' in locals() and fish_sites and macro_sites:
        overlap = set(fish_sites) & set(macro_sites)
        print(f"\n3. Sites with both fish and macro data: {len(overlap)}")
        if overlap:
            print(f"   Example sites with both: {list(overlap)[:3]}")
    
    print("\n" + "-" * 50)
    print("Test complete!")

if __name__ == "__main__":
    test_site_data_functions()