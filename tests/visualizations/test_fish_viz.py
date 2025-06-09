#!/usr/bin/env python3
"""
Fish Visualization Tests - Runnable Script Version

To run specific tests, set the flags below to True/False
To run all tests: python test_fish_viz.py
"""

from data_processing.fish_processing import (
    get_fish_dataframe, 
    get_fish_metrics_data_for_table,
    get_sites_with_fish_data
)
from data_processing.fish_viz import (
    create_fish_viz, 
    create_fish_metrics_table_for_accordion
)

# ============================================================================
# CONFIGURATION - Set these to True/False to run specific tests
# ============================================================================
RUN_BASIC_CHECK = True
RUN_KNOWN_SITES = False
RUN_DATA_VALIDATION = False
RUN_EDGE_CASES = False
RUN_VISUAL_SAMPLES = False
SHOW_CHARTS = False  # Set to True to display charts in browser
SAVE_CHARTS = False  # Set to True to save HTML files

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def print_section_header(title):
    print("\n" + "="*80)
    print(f"🔍 {title}")
    print("="*80)

def print_test_header(title):
    print(f"\n📊 {title}")
    print("-" * 50)

def safe_execute(test_name, test_function):
    """Safely execute a test function and report results"""
    try:
        print_test_header(test_name)
        test_function()
        print(f"✅ {test_name} completed successfully")
        return True
    except Exception as e:
        print(f"❌ {test_name} failed: {e}")
        import traceback
        print("Full error traceback:")
        traceback.print_exc()
        return False

# ============================================================================
# TEST FUNCTIONS
# ============================================================================

def test_basic_system_check():
    """Test basic database connectivity and data retrieval"""
    # Check if we can get a list of sites
    sites = get_sites_with_fish_data()
    print(f"✅ Found {len(sites)} sites with fish data")
    
    if len(sites) > 0:
        print(f"📋 First 10 sites: {sites[:10]}")
    
    # Check if we can get all fish data
    all_data = get_fish_dataframe()
    print(f"✅ Retrieved {len(all_data)} total fish records")
    
    if not all_data.empty:
        print(f"📅 Years covered: {all_data['year'].min()} - {all_data['year'].max()}")
        print(f"🏞️  Unique sites: {all_data['site_name'].nunique()}")
        print(f"📊 Sample integrity classes: {all_data['integrity_class'].value_counts().head()}")

def test_known_sites():
    """Test sites we know should have data"""
    test_sites = [
        "Baron Fork River: Welling Road",
        "Spring Creek: Cavalier Road", 
        "Chisholm Creek: Western",
        "East Cache Creek: Big Green",
    ]
    
    successful_sites = []
    failed_sites = []
    
    for site_name in test_sites:
        print(f"\n🔍 Testing: {site_name}")
        
        try:
            # Test data retrieval
            site_data = get_fish_dataframe(site_name)
            
            if site_data.empty:
                print(f"❌ No data found for {site_name}")
                failed_sites.append(site_name)
                continue
                
            print(f"✅ Found {len(site_data)} records")
            print(f"📅 Years: {sorted(site_data['year'].tolist())}")
            print(f"🏆 Integrity classes: {site_data['integrity_class'].tolist()}")
            print(f"📊 IBI scores: {[round(x, 3) for x in site_data['comparison_to_reference'].tolist()]}")
            
            # Test visualization creation
            fig = create_fish_viz(site_name)
            print(f"✅ Created visualization successfully")
            print(f"📈 Chart title: {fig.layout.title.text}")
            
            if SHOW_CHARTS:
                fig.show()
                
            if SAVE_CHARTS:
                filename = f"test_chart_{site_name.replace(':', '_').replace(' ', '_')}.html"
                fig.write_html(filename)
                print(f"💾 Saved chart: {filename}")
            
            # Test metrics table
            create_fish_metrics_table_for_accordion(site_name)
            print(f"✅ Created metrics table successfully")
            
            successful_sites.append(site_name)
            
        except Exception as e:
            print(f"❌ Error testing {site_name}: {e}")
            failed_sites.append(site_name)
    
    print(f"\n📊 SUMMARY: {len(successful_sites)} successful, {len(failed_sites)} failed")
    if failed_sites:
        print(f"❌ Failed sites: {failed_sites}")

def test_data_structure_validation():
    """Deep dive into data structure for one site"""
    test_site = "Baron Fork River: Welling Road"
    print(f"📍 Detailed inspection of: {test_site}")
    
    # Get the data
    site_data = get_fish_dataframe(test_site)
    metrics_df, summary_df = get_fish_metrics_data_for_table(test_site)
    
    print("\n📊 MAIN DATA STRUCTURE:")
    print(f"Shape: {site_data.shape}")
    print(f"Columns: {list(site_data.columns)}")
    print(f"Data types:\n{site_data.dtypes}")
    
    if not site_data.empty:
        print("\n📋 First few rows:")
        print(site_data.to_string())
    
    print("\n📋 METRICS DATA STRUCTURE:")
    if not metrics_df.empty:
        print(f"Shape: {metrics_df.shape}")
        print(f"Columns: {list(metrics_df.columns)}")
        print(f"Unique metrics: {sorted(metrics_df['metric_name'].unique())}")
        print("\nSample metrics data:")
        print(metrics_df.head().to_string())
    else:
        print("❌ No metrics data found")
    
    print("\n📈 SUMMARY DATA STRUCTURE:")
    if not summary_df.empty:
        print(f"Shape: {summary_df.shape}")
        print(f"Columns: {list(summary_df.columns)}")
        print("\nSample summary data:")
        print(summary_df.head().to_string())
    else:
        print("❌ No summary data found")

def test_edge_cases():
    """Test error handling for edge cases"""
    edge_cases = [
        ("Non-existent site", "This Site Does Not Exist"),
        ("Empty site name", ""),
        ("None value", None),
    ]
    
    for test_name, site_input in edge_cases:
        print(f"\n🧪 Testing {test_name}: {repr(site_input)}")
        
        try:
            data = get_fish_dataframe(site_input)
            if data.empty:
                print("✅ Correctly returned empty DataFrame")
            else:
                print(f"⚠️  Unexpected: got {len(data)} records")
                
            fig = create_fish_viz(site_input)
            print("✅ Visualization handled gracefully")
            print(f"📊 Title: {fig.layout.title.text}")
            
        except Exception as e:
            print(f"❌ Error with {test_name}: {e}")

def test_visual_samples():
    """Create sample visualizations for manual inspection"""
    sample_sites = ["Baron Fork River: Welling Road", "Chisholm Creek: Western"]
    
    for site_name in sample_sites:
        print(f"\n🎨 Creating sample visualization for: {site_name}")
        
        try:
            data = get_fish_dataframe(site_name)
            if data.empty:
                print(f"❌ No data for {site_name}")
                continue
                
            fig = create_fish_viz(site_name)
            print(f"✅ Visualization created")
            
            # Always save sample charts for manual inspection
            filename = f"SAMPLE_{site_name.replace(':', '_').replace(' ', '_')}.html"
            fig.write_html(filename)
            print(f"💾 Saved sample chart: {filename}")
            
            if SHOW_CHARTS:
                fig.show()
                
        except Exception as e:
            print(f"❌ Error creating sample for {site_name}: {e}")

# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    print("🐟 FISH VISUALIZATION TESTING SUITE")
    print("=" * 80)
    
    test_results = {}
    
    if RUN_BASIC_CHECK:
        test_results['basic_check'] = safe_execute("Basic System Check", test_basic_system_check)
    
    if RUN_KNOWN_SITES:
        test_results['known_sites'] = safe_execute("Known Sites Test", test_known_sites)
    
    if RUN_DATA_VALIDATION:
        test_results['data_validation'] = safe_execute("Data Structure Validation", test_data_structure_validation)
    
    if RUN_EDGE_CASES:
        test_results['edge_cases'] = safe_execute("Edge Cases Test", test_edge_cases)
    
    if RUN_VISUAL_SAMPLES:
        test_results['visual_samples'] = safe_execute("Visual Samples Creation", test_visual_samples)
    
    # Final summary
    print_section_header("TEST SUMMARY")
    successful_tests = sum(test_results.values())
    total_tests = len(test_results)
    
    print(f"📊 Tests completed: {total_tests}")
    print(f"✅ Successful: {successful_tests}")
    print(f"❌ Failed: {total_tests - successful_tests}")
    
    if successful_tests == total_tests:
        print("\n🎉 ALL TESTS PASSED! Your fish visualization pipeline is working!")
    else:
        print("\n⚠️  Some tests failed. Check the output above for details.")
        
    print("\n💡 Next steps:")
    print("1. Check any saved HTML files for visual inspection")
    print("2. Set SHOW_CHARTS = True to see charts in browser")
    print("3. Investigate any failed tests")

if __name__ == "__main__":
    main()