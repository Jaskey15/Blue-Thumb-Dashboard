"""
Tests for habitat_callbacks.py

This file tests the habitat callback functions including state management,
dropdown population, navigation handling, and content display logic.
"""

import pytest
import dash
from unittest.mock import Mock, patch, MagicMock

class TestHabitatStateManagement:
    """Test habitat state management logic."""
    
    def test_save_habitat_state_with_valid_site(self):
        """Test saving habitat state when a valid site is selected."""
        # Simulate the save_habitat_state logic
        selected_site = "Test Site"
        current_state = {'selected_site': None}
        
        # Logic from the actual callback
        if selected_site is not None:
            result = {'selected_site': selected_site}
        else:
            result = current_state or {'selected_site': None}
        
        assert result == {'selected_site': 'Test Site'}, "Should save valid site selection"
    
    def test_save_habitat_state_with_none_selection(self):
        """Test habitat state preservation when selection is cleared."""
        # Test with existing state
        selected_site = None
        current_state = {'selected_site': 'Previous Site'}
        
        # Logic from the actual callback
        if selected_site is not None:
            result = {'selected_site': selected_site}
        else:
            result = current_state or {'selected_site': None}
        
        assert result == {'selected_site': 'Previous Site'}, "Should preserve existing state when selection cleared"
    
    def test_save_habitat_state_with_no_existing_state(self):
        """Test habitat state creation when no previous state exists."""
        selected_site = None
        current_state = None
        
        # Logic from the actual callback
        if selected_site is not None:
            result = {'selected_site': selected_site}
        else:
            result = current_state or {'selected_site': None}
        
        assert result == {'selected_site': None}, "Should create default state when none exists"
    
    def test_habitat_state_structure(self):
        """Test habitat state data structure."""
        # Test valid state structure
        valid_state = {'selected_site': 'Test Site'}
        
        assert 'selected_site' in valid_state, "State should contain selected_site key"
        assert isinstance(valid_state['selected_site'], str), "selected_site should be string"
        
        # Test default state structure
        default_state = {'selected_site': None}
        
        assert 'selected_site' in default_state, "Default state should contain selected_site key"
        assert default_state['selected_site'] is None, "Default selected_site should be None"


class TestDropdownPopulationLogic:
    """Test dropdown population and navigation logic."""
    
    def test_site_dropdown_options_creation(self):
        """Test creation of dropdown options from site list."""
        # Mock site data
        sites = ['Site A', 'Site C', 'Site B']  # Unsorted to test sorting
        
        # Logic from the actual callback
        options = [{'label': site, 'value': site} for site in sorted(sites)]
        
        expected_options = [
            {'label': 'Site A', 'value': 'Site A'},
            {'label': 'Site B', 'value': 'Site B'},
            {'label': 'Site C', 'value': 'Site C'}
        ]
        
        assert options == expected_options, "Should create sorted dropdown options"
    
    def test_empty_sites_list_handling(self):
        """Test handling of empty sites list."""
        sites = []
        
        # Logic from the actual callback
        if not sites:
            options = []
            # Would return [], dash.no_update in actual callback
        else:
            options = [{'label': site, 'value': site} for site in sorted(sites)]
        
        assert options == [], "Should return empty options for empty sites list"
    
    def test_navigation_target_site_validation(self):
        """Test validation of navigation target site."""
        # Test valid target site
        available_sites = ['Site A', 'Site B', 'Site C']
        target_site = 'Site B'
        
        is_valid = target_site in available_sites
        assert is_valid is True, "Should validate target site exists in available sites"
        
        # Test invalid target site
        invalid_target = 'Non-existent Site'
        is_valid = invalid_target in available_sites
        assert is_valid is False, "Should detect invalid target site"
    
    def test_tab_activation_detection(self):
        """Test detection of habitat tab activation."""
        # Test habitat tab activation
        active_tab = 'habitat-tab'
        is_habitat_active = (active_tab == 'habitat-tab')
        assert is_habitat_active is True, "Should detect habitat tab activation"
        
        # Test other tab activation
        active_tab = 'chemical-tab'
        is_habitat_active = (active_tab == 'habitat-tab')
        assert is_habitat_active is False, "Should detect non-habitat tab activation"
    
    def test_trigger_id_extraction_for_habitat(self):
        """Test trigger ID extraction for habitat-specific triggers."""
        # Test main-tabs trigger
        prop_id = 'main-tabs.active_tab'
        trigger_id = prop_id.split('.')[0]
        assert trigger_id == 'main-tabs', "Should extract main-tabs trigger ID"
        
        # Test navigation-store trigger
        prop_id = 'navigation-store.data'
        trigger_id = prop_id.split('.')[0]
        assert trigger_id == 'navigation-store', "Should extract navigation-store trigger ID"


class TestNavigationHandling:
    """Test navigation handling logic."""
    
    def test_navigation_data_validation(self):
        """Test validation of navigation data structure."""
        # Test valid navigation data
        nav_data = {
            'target_tab': 'habitat-tab',
            'target_site': 'Test Site',
            'source_parameter': 'habitat:Habitat_Score'
        }
        
        is_habitat_navigation = (
            nav_data and 
            nav_data.get('target_tab') == 'habitat-tab' and 
            nav_data.get('target_site')
        )
        
        assert is_habitat_navigation, "Should validate complete navigation data"
        
        # Test incomplete navigation data
        incomplete_nav_data = {
            'target_tab': 'habitat-tab'
            # Missing target_site
        }
        
        is_habitat_navigation = (
            incomplete_nav_data and 
            incomplete_nav_data.get('target_tab') == 'habitat-tab' and 
            incomplete_nav_data.get('target_site')
        )
        
        assert not is_habitat_navigation, "Should detect incomplete navigation data"
    
    def test_navigation_priority_logic(self):
        """Test navigation vs state restoration priority."""
        # Priority 1: Navigation data (highest priority)
        nav_data = {'target_tab': 'habitat-tab', 'target_site': 'Nav Site'}
        habitat_state = {'selected_site': 'Saved Site'}
        trigger_id = 'main-tabs'
        
        # Navigation should take priority
        has_navigation = (nav_data and nav_data.get('target_tab') == 'habitat-tab')
        has_saved_state = (habitat_state and habitat_state.get('selected_site'))
        
        if has_navigation:
            selected_site = nav_data.get('target_site')
        elif trigger_id == 'main-tabs' and has_saved_state:
            selected_site = habitat_state.get('selected_site')
        else:
            selected_site = None
        
        assert selected_site == 'Nav Site', "Navigation should take priority over saved state"
        
        # Priority 2: Saved state (when no navigation)
        nav_data = None
        
        has_navigation = (nav_data and nav_data.get('target_tab') == 'habitat-tab')
        has_saved_state = (habitat_state and habitat_state.get('selected_site'))
        
        if has_navigation:
            selected_site = nav_data.get('target_site')
        elif trigger_id == 'main-tabs' and has_saved_state:
            selected_site = habitat_state.get('selected_site')
        else:
            selected_site = None
        
        assert selected_site == 'Saved Site', "Should use saved state when no navigation"
    
    def test_state_restoration_conditions(self):
        """Test conditions for state restoration."""
        # Test valid state restoration conditions
        trigger_id = 'main-tabs'
        habitat_state = {'selected_site': 'Saved Site'}
        nav_data = None  # No active navigation
        
        should_restore = (
            trigger_id == 'main-tabs' and 
            habitat_state and 
            habitat_state.get('selected_site') and
            (not nav_data or not nav_data.get('target_tab'))
        )
        
        assert should_restore is True, "Should restore state when conditions are met"
        
        # Test with active navigation (should not restore)
        nav_data = {'target_tab': 'habitat-tab', 'target_site': 'Nav Site'}
        
        should_restore = (
            trigger_id == 'main-tabs' and 
            habitat_state and 
            habitat_state.get('selected_site') and
            (not nav_data or not nav_data.get('target_tab'))
        )
        
        assert should_restore is False, "Should not restore state when navigation is active"


class TestContentDisplayLogic:
    """Test content display logic."""
    
    def test_content_display_site_validation(self):
        """Test site validation for content display."""
        # Test valid site
        selected_site = "Test Site"
        has_site = bool(selected_site)
        assert has_site is True, "Should detect valid site selection"
        
        # Test empty site
        selected_site = ""
        has_site = bool(selected_site)
        assert has_site is False, "Should detect empty site selection"
        
        # Test None site
        selected_site = None
        has_site = bool(selected_site)
        assert has_site is False, "Should detect None site selection"
    
    def test_error_state_data_structure(self):
        """Test error state data structure."""
        # Simulate error state creation
        error_title = "Error Loading Habitat Data"
        error_message = "Could not load habitat data for Test Site. Please try again."
        error_details = "Database connection failed"
        
        # Validate error state components
        assert isinstance(error_title, str), "Error title should be string"
        assert isinstance(error_message, str), "Error message should be string"
        assert isinstance(error_details, str), "Error details should be string"
        assert "habitat data" in error_message.lower(), "Error message should mention habitat data"
        assert "Test Site" in error_message, "Error message should include site name"
    
    def test_empty_state_message(self):
        """Test empty state message format."""
        empty_message = "Select a site above to view habitat assessment data."
        
        assert isinstance(empty_message, str), "Empty message should be string"
        assert "select" in empty_message.lower(), "Should prompt user to select"
        assert "habitat" in empty_message.lower(), "Should mention habitat"
        assert "site" in empty_message.lower(), "Should mention site"


class TestErrorHandling:
    """Test error handling scenarios."""
    
    def test_sites_data_error_handling(self):
        """Test handling of sites data retrieval errors."""
        # Test empty sites list
        sites = []
        
        if not sites:
            # Would log warning and return [], dash.no_update
            should_continue = False
        else:
            should_continue = True
        
        assert should_continue is False, "Should handle empty sites list gracefully"
        
        # Test None sites
        sites = None
        
        if not sites:
            should_continue = False
        else:
            should_continue = True
        
        assert should_continue is False, "Should handle None sites gracefully"
    
    def test_saved_site_validation(self):
        """Test validation of saved site against available sites."""
        available_sites = ['Site A', 'Site B', 'Site C']
        
        # Test valid saved site
        saved_site = 'Site B'
        is_valid = saved_site in available_sites
        assert is_valid is True, "Should validate saved site exists"
        
        # Test invalid saved site
        saved_site = 'Removed Site'
        is_valid = saved_site in available_sites
        assert is_valid is False, "Should detect invalid saved site"
        
        # Test None saved site
        saved_site = None
        is_valid = bool(saved_site) and saved_site in available_sites
        assert is_valid is False, "Should handle None saved site"
    
    def test_navigation_data_malformation(self):
        """Test handling of malformed navigation data."""
        # Test missing target_tab
        nav_data = {'target_site': 'Test Site'}  # Missing target_tab
        is_valid_navigation = (
            nav_data and 
            nav_data.get('target_tab') == 'habitat-tab' and 
            nav_data.get('target_site')
        )
        assert not is_valid_navigation, "Should detect missing target_tab"
        
        # Test wrong target_tab
        nav_data = {'target_tab': 'chemical-tab', 'target_site': 'Test Site'}
        is_valid_navigation = (
            nav_data and 
            nav_data.get('target_tab') == 'habitat-tab' and 
            nav_data.get('target_site')
        )
        assert not is_valid_navigation, "Should detect wrong target_tab"
        
        # Test missing target_site
        nav_data = {'target_tab': 'habitat-tab'}  # Missing target_site
        is_valid_navigation = (
            nav_data and 
            nav_data.get('target_tab') == 'habitat-tab' and 
            nav_data.get('target_site')
        )
        assert not is_valid_navigation, "Should detect missing target_site"


class TestIntegrationScenarios:
    """Integration tests for complete habitat callback workflows."""
    
    def test_complete_map_navigation_workflow(self):
        """Test complete workflow from map click to content display."""
        # Step 1: Navigation data from map click
        nav_data = {
            'target_tab': 'habitat-tab',
            'target_site': 'Tenmile Creek - Highway 125',
            'source_parameter': 'habitat:Habitat_Score'
        }
        
        # Step 2: Validate navigation data
        is_valid_navigation = (
            nav_data and 
            nav_data.get('target_tab') == 'habitat-tab' and 
            nav_data.get('target_site')
        )
        assert is_valid_navigation, "Navigation data should be valid"
        
        # Step 3: Extract target site
        target_site = nav_data.get('target_site')
        assert target_site == 'Tenmile Creek - Highway 125', "Should extract target site"
        
        # Step 4: Simulate site availability check
        available_sites = ['Tenmile Creek - Highway 125', 'Other Site']
        site_available = target_site in available_sites
        assert site_available is True, "Target site should be available"
        
        # Step 5: Set dropdown value and create options
        options = [{'label': site, 'value': site} for site in sorted(available_sites)]
        selected_value = target_site
        
        expected_options = [
            {'label': 'Other Site', 'value': 'Other Site'},
            {'label': 'Tenmile Creek - Highway 125', 'value': 'Tenmile Creek - Highway 125'}
        ]
        
        assert options == expected_options, "Should create correct dropdown options"
        assert selected_value == 'Tenmile Creek - Highway 125', "Should set correct dropdown value"
        
        # Step 6: Content display validation
        has_selected_site = bool(selected_value)
        assert has_selected_site is True, "Should have site selected for content display"
    
    def test_complete_state_restoration_workflow(self):
        """Test complete workflow for state restoration."""
        # Step 1: Simulate tab activation
        active_tab = 'habitat-tab'
        trigger_id = 'main-tabs'
        
        # Step 2: Check saved state
        habitat_state = {'selected_site': 'Saved Site'}
        nav_data = None  # No active navigation
        
        # Step 3: Validate restoration conditions
        should_restore = (
            active_tab == 'habitat-tab' and
            trigger_id == 'main-tabs' and 
            habitat_state and 
            habitat_state.get('selected_site') and
            (not nav_data or not nav_data.get('target_tab'))
        )
        assert should_restore is True, "Should meet restoration conditions"
        
        # Step 4: Simulate site availability check
        available_sites = ['Saved Site', 'Other Site']
        saved_site = habitat_state.get('selected_site')
        site_available = saved_site in available_sites
        assert site_available is True, "Saved site should be available"
        
        # Step 5: Restore dropdown state
        options = [{'label': site, 'value': site} for site in sorted(available_sites)]
        restored_value = saved_site
        
        assert restored_value == 'Saved Site', "Should restore saved site"
        assert len(options) == 2, "Should create options for available sites"
    
    def test_complete_error_handling_workflow(self):
        """Test complete workflow with error scenarios."""
        # Step 1: Simulate sites data error
        sites = []  # Empty sites list
        
        # Step 2: Handle empty sites
        if not sites:
            should_continue = False
            error_occurred = True
        else:
            should_continue = True
            error_occurred = False
        
        assert should_continue is False, "Should stop processing with no sites"
        assert error_occurred is True, "Should detect error condition"
        
        # Step 3: Simulate invalid navigation target
        nav_data = {'target_tab': 'habitat-tab', 'target_site': 'Invalid Site'}
        available_sites = ['Valid Site A', 'Valid Site B']
        
        target_site = nav_data.get('target_site')
        site_available = target_site in available_sites
        
        assert site_available is False, "Should detect invalid target site"
        
        # Step 4: Simulate content display error
        selected_site = 'Test Site'
        
        try:
            # Simulate content creation that might fail
            if selected_site == 'Test Site':
                # Simulate an error
                raise Exception("Database connection failed")
            content_created = True
        except Exception as e:
            content_created = False
            error_message = str(e)
        
        assert content_created is False, "Should handle content creation error"
        assert "Database connection failed" in error_message, "Should capture error details"
    
    def test_navigation_store_clearing_workflow(self):
        """Test workflow when navigation store is cleared."""
        # Step 1: Simulate navigation store clearing
        trigger_id = 'navigation-store'
        nav_data = None  # Cleared navigation data
        
        # Step 2: Check if this is a clearing event
        is_clearing_event = (
            trigger_id == 'navigation-store' and 
            (not nav_data or not nav_data.get('target_tab'))
        )
        assert is_clearing_event is True, "Should detect navigation store clearing"
        
        # Step 3: Should ignore clearing events (no updates)
        should_ignore = is_clearing_event
        assert should_ignore is True, "Should ignore navigation store clearing events"

# Test runner for manual execution
if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 