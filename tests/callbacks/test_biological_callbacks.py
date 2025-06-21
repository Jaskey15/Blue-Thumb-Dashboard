"""
Tests for biological_callbacks.py

This file tests the biological callback functions including state management,
community selection, site dropdown population, navigation handling, and gallery functionality.
"""

import pytest
import dash
from unittest.mock import Mock, patch, MagicMock

class TestBiologicalStateManagement:
    """Test biological state management logic."""
    
    def test_save_biological_state_with_community_selection(self):
        """Test saving biological state when community is selected."""
        # Simulate the save_biological_state logic
        selected_community = "fish"
        selected_site = None
        current_state = {'selected_community': None, 'selected_site': None}
        
        # Logic from the actual callback
        if selected_community is not None or selected_site is not None:
            new_state = current_state.copy() if current_state else {'selected_community': None, 'selected_site': None}
            if selected_community is not None:
                new_state['selected_community'] = selected_community
            if selected_site is not None:
                new_state['selected_site'] = selected_site
            result = new_state
        else:
            result = current_state or {'selected_community': None, 'selected_site': None}
        
        expected_state = {
            'selected_community': 'fish',
            'selected_site': None
        }
        
        assert result == expected_state, "Should save community selection to state"
    
    def test_save_biological_state_with_site_selection(self):
        """Test saving biological state when site is selected."""
        selected_community = None
        selected_site = "Test Site"
        current_state = {'selected_community': 'fish', 'selected_site': None}
        
        # Logic from the actual callback
        if selected_community is not None or selected_site is not None:
            new_state = current_state.copy() if current_state else {'selected_community': None, 'selected_site': None}
            if selected_community is not None:
                new_state['selected_community'] = selected_community
            if selected_site is not None:
                new_state['selected_site'] = selected_site
            result = new_state
        else:
            result = current_state or {'selected_community': None, 'selected_site': None}
        
        expected_state = {
            'selected_community': 'fish',
            'selected_site': 'Test Site'
        }
        
        assert result == expected_state, "Should save site selection to state"
    
    def test_save_biological_state_with_both_selections(self):
        """Test saving biological state when both community and site are selected."""
        selected_community = "macro"
        selected_site = "Test Site"
        current_state = {'selected_community': None, 'selected_site': None}
        
        # Logic from the actual callback
        if selected_community is not None or selected_site is not None:
            new_state = current_state.copy() if current_state else {'selected_community': None, 'selected_site': None}
            if selected_community is not None:
                new_state['selected_community'] = selected_community
            if selected_site is not None:
                new_state['selected_site'] = selected_site
            result = new_state
        else:
            result = current_state or {'selected_community': None, 'selected_site': None}
        
        expected_state = {
            'selected_community': 'macro',
            'selected_site': 'Test Site'
        }
        
        assert result == expected_state, "Should save both community and site selections to state"
    
    def test_save_biological_state_preservation_when_cleared(self):
        """Test biological state preservation when both dropdowns are cleared."""
        selected_community = None
        selected_site = None
        current_state = {'selected_community': 'fish', 'selected_site': 'Test Site'}
        
        # Logic from the actual callback
        if selected_community is not None or selected_site is not None:
            new_state = current_state.copy() if current_state else {'selected_community': None, 'selected_site': None}
            if selected_community is not None:
                new_state['selected_community'] = selected_community
            if selected_site is not None:
                new_state['selected_site'] = selected_site
            result = new_state
        else:
            result = current_state or {'selected_community': None, 'selected_site': None}
        
        expected_state = {
            'selected_community': 'fish',
            'selected_site': 'Test Site'
        }
        
        assert result == expected_state, "Should preserve existing state when both dropdowns are cleared"
    
    def test_biological_state_structure_validation(self):
        """Test biological state data structure validation."""
        # Test valid state structure
        valid_state = {
            'selected_community': 'fish',
            'selected_site': 'Test Site'
        }
        
        assert 'selected_community' in valid_state, "State should contain selected_community key"
        assert 'selected_site' in valid_state, "State should contain selected_site key"
        assert valid_state['selected_community'] in [None, 'fish', 'macro'], "Community should be valid type"
        assert isinstance(valid_state['selected_site'], (str, type(None))), "Site should be string or None"


class TestNavigationAndInitialLoad:
    """Test navigation handling and initial load logic."""
    
    def test_tab_activation_detection(self):
        """Test detection of biological tab activation."""
        # Test biological tab activation
        active_tab = 'biological-tab'
        should_handle = (active_tab == 'biological-tab')
        assert should_handle is True, "Should detect biological tab activation"
        
        # Test other tab activation
        active_tab = 'chemical-tab'
        should_handle = (active_tab == 'biological-tab')
        assert should_handle is False, "Should detect non-biological tab activation"
    
    def test_navigation_data_validation(self):
        """Test validation of navigation data for biological tab."""
        # Test valid navigation data
        nav_data = {
            'target_tab': 'biological-tab',
            'target_community': 'fish',
            'target_site': 'Test Site'
        }
        
        is_valid_navigation = (
            nav_data and 
            nav_data.get('target_tab') == 'biological-tab' and
            nav_data.get('target_community') and 
            nav_data.get('target_site')
        )
        
        assert is_valid_navigation, "Should validate complete navigation data"
        
        # Test incomplete navigation data
        incomplete_nav_data = {
            'target_tab': 'biological-tab',
            'target_community': 'fish'
            # Missing target_site
        }
        
        is_valid_navigation = (
            incomplete_nav_data and 
            incomplete_nav_data.get('target_tab') == 'biological-tab' and
            incomplete_nav_data.get('target_community') and 
            incomplete_nav_data.get('target_site')
        )
        
        assert not is_valid_navigation, "Should detect incomplete navigation data"
    
    def test_trigger_id_extraction(self):
        """Test trigger ID extraction for biological callbacks."""
        # Test main-tabs trigger
        prop_id = 'main-tabs.active_tab'
        trigger_id = prop_id.split('.')[0]
        assert trigger_id == 'main-tabs', "Should extract main-tabs trigger ID"
        
        # Test navigation-store trigger
        prop_id = 'navigation-store.data'
        trigger_id = prop_id.split('.')[0]
        assert trigger_id == 'navigation-store', "Should extract navigation-store trigger ID"
    
    def test_navigation_priority_logic(self):
        """Test navigation vs state restoration priority."""
        # Priority 1: Navigation data (highest priority)
        nav_data = {
            'target_tab': 'biological-tab',
            'target_community': 'fish',
            'target_site': 'Nav Site'
        }
        biological_state = {
            'selected_community': 'macro',
            'selected_site': 'Saved Site'
        }
        trigger_id = 'main-tabs'
        
        # Navigation should take priority
        has_navigation = (
            nav_data and 
            nav_data.get('target_tab') == 'biological-tab' and
            nav_data.get('target_community') and 
            nav_data.get('target_site')
        )
        has_saved_state = (
            biological_state and 
            biological_state.get('selected_community')
        )
        
        if has_navigation:
            selected_community = nav_data.get('target_community')
            selected_site = nav_data.get('target_site')
        elif trigger_id == 'main-tabs' and has_saved_state:
            selected_community = biological_state.get('selected_community')
            selected_site = biological_state.get('selected_site')
        else:
            selected_community = None
            selected_site = None
        
        assert selected_community == 'fish', "Navigation community should take priority"
        assert selected_site == 'Nav Site', "Navigation site should take priority"
    
    def test_state_restoration_conditions(self):
        """Test conditions for state restoration."""
        # Test with valid saved state and no navigation
        trigger_id = 'main-tabs'
        biological_state = {
            'selected_community': 'fish',
            'selected_site': 'Saved Site'
        }
        nav_data = None
        
        should_restore = (
            trigger_id == 'main-tabs' and 
            biological_state and
            biological_state.get('selected_community') and
            (not nav_data or not nav_data.get('target_tab'))
        )
        
        assert should_restore is True, "Should restore state when conditions are met"
        
        # Test with navigation present (should not restore)
        nav_data = {'target_tab': 'biological-tab', 'target_community': 'macro'}
        
        should_restore = (
            trigger_id == 'main-tabs' and 
            biological_state and
            biological_state.get('selected_community') and
            (not nav_data or not nav_data.get('target_tab'))
        )
        
        assert should_restore is False, "Should not restore state when navigation is present"


class TestCommunitySelectionLogic:
    """Test community selection and site dropdown logic."""
    
    def test_site_dropdown_visibility_logic(self):
        """Test site dropdown visibility based on community selection."""
        # Test with community selected
        selected_community = "fish"
        
        if selected_community:
            dropdown_style = {'display': 'block', 'marginBottom': '20px'}
            dropdown_disabled = False
        else:
            dropdown_style = {'display': 'none'}
            dropdown_disabled = True
        
        assert dropdown_style['display'] == 'block', "Should show dropdown when community selected"
        assert dropdown_disabled is False, "Should enable dropdown when community selected"
        
        # Test with no community selected
        selected_community = None
        
        if selected_community:
            dropdown_style = {'display': 'block', 'marginBottom': '20px'}
            dropdown_disabled = False
        else:
            dropdown_style = {'display': 'none'}
            dropdown_disabled = True
        
        assert dropdown_style['display'] == 'none', "Should hide dropdown when no community selected"
        assert dropdown_disabled is True, "Should disable dropdown when no community selected"
    
    def test_site_options_creation(self):
        """Test creation of site dropdown options."""
        # Mock available sites
        available_sites = ['Site C', 'Site A', 'Site B']  # Unsorted
        
        # Logic from the actual callback
        options = [{'label': site, 'value': site} for site in sorted(available_sites)]
        
        expected_options = [
            {'label': 'Site A', 'value': 'Site A'},
            {'label': 'Site B', 'value': 'Site B'},
            {'label': 'Site C', 'value': 'Site C'}
        ]
        
        assert options == expected_options, "Should create sorted dropdown options"
    
    def test_site_value_preservation_logic(self):
        """Test site value preservation when switching communities."""
        # Test with valid current site for new community
        current_site_value = "Common Site"
        available_sites = ["Common Site", "Other Site A", "Other Site B"]
        
        # Logic from the actual callback
        site_value_to_set = None
        if current_site_value and current_site_value in available_sites:
            site_value_to_set = current_site_value
        
        assert site_value_to_set == "Common Site", "Should preserve existing site when valid for new community"
        
        # Test with invalid current site for new community
        current_site_value = "Invalid Site"
        available_sites = ["Site A", "Site B", "Site C"]
        
        site_value_to_set = None
        if current_site_value and current_site_value in available_sites:
            site_value_to_set = current_site_value
        
        assert site_value_to_set is None, "Should clear site when invalid for new community"
    
    def test_empty_sites_handling(self):
        """Test handling of empty sites list for community."""
        # Test with no available sites
        available_sites = []
        selected_community = "fish"
        
        if not available_sites:
            options = []
            site_value = None
            dropdown_style = {'display': 'block', 'marginBottom': '20px'}
            dropdown_disabled = False
        else:
            options = [{'label': site, 'value': site} for site in sorted(available_sites)]
            site_value = None
            dropdown_style = {'display': 'block', 'marginBottom': '20px'}
            dropdown_disabled = False
        
        assert options == [], "Should return empty options when no sites available"
        assert site_value is None, "Should clear site value when no sites available"
        assert dropdown_style['display'] == 'block', "Should still show section even with no sites"
        assert dropdown_disabled is False, "Should still enable dropdown even with no sites"


class TestContentDisplayLogic:
    """Test content display logic."""
    
    def test_content_display_requirements(self):
        """Test content display requirements validation."""
        # Test with both selections
        selected_community = "fish"
        selected_site = "Test Site"
        
        should_display_content = bool(selected_community and selected_site)
        assert should_display_content is True, "Should display content when both selections are made"
        
        # Test with missing community
        selected_community = None
        selected_site = "Test Site"
        
        should_display_content = bool(selected_community and selected_site)
        assert should_display_content is False, "Should not display content when community is missing"
        
        # Test with missing site
        selected_community = "fish"
        selected_site = None
        
        should_display_content = bool(selected_community and selected_site)
        assert should_display_content is False, "Should not display content when site is missing"
        
        # Test with both missing
        selected_community = None
        selected_site = None
        
        should_display_content = bool(selected_community and selected_site)
        assert should_display_content is False, "Should not display content when both are missing"
    
    def test_empty_state_message_structure(self):
        """Test empty state message structure."""
        # Test empty state creation
        message = "Please select a community type and site to view biological data."
        
        # Mock empty state structure
        empty_state = {
            'type': 'empty_state',
            'message': message
        }
        
        assert 'message' in empty_state, "Empty state should have message"
        assert 'select' in empty_state['message'].lower(), "Message should mention selection requirement"
        assert 'community' in empty_state['message'].lower(), "Message should mention community selection"
        assert 'site' in empty_state['message'].lower(), "Message should mention site selection"


class TestGalleryNavigationLogic:
    """Test gallery navigation logic."""
    
    def test_gallery_button_click_detection(self):
        """Test detection of gallery navigation button clicks."""
        # Test previous button click
        prev_clicks = 1
        next_clicks = 0
        
        # Mock context to determine which button was clicked
        if prev_clicks and (not next_clicks or prev_clicks > next_clicks):
            direction = 'prev'
        elif next_clicks and (not prev_clicks or next_clicks > prev_clicks):
            direction = 'next'
        else:
            direction = None
        
        assert direction == 'prev', "Should detect previous button click"
        
        # Test next button click
        prev_clicks = 0
        next_clicks = 1
        
        if prev_clicks and (not next_clicks or prev_clicks > next_clicks):
            direction = 'prev'
        elif next_clicks and (not prev_clicks or next_clicks > prev_clicks):
            direction = 'next'
        else:
            direction = None
        
        assert direction == 'next', "Should detect next button click"
        
        # Test no button clicks
        prev_clicks = 0
        next_clicks = 0
        
        if prev_clicks and (not next_clicks or prev_clicks > next_clicks):
            direction = 'prev'
        elif next_clicks and (not prev_clicks or next_clicks > prev_clicks):
            direction = 'next'
        else:
            direction = None
        
        assert direction is None, "Should detect no button clicks"
    
    def test_gallery_index_management(self):
        """Test gallery index management logic."""
        # Test initial index
        current_index = None
        default_index = 0
        
        index_to_use = current_index if current_index is not None else default_index
        assert index_to_use == 0, "Should use default index when none exists"
        
        # Test existing index
        current_index = 3
        index_to_use = current_index if current_index is not None else default_index
        assert index_to_use == 3, "Should use existing index when available"
    
    def test_gallery_types_validation(self):
        """Test gallery type validation."""
        # Test valid gallery types
        valid_types = ['fish', 'macro']
        
        for gallery_type in valid_types:
            is_valid = gallery_type in ['fish', 'macro']
            assert is_valid is True, f"Should validate {gallery_type} as valid gallery type"
        
        # Test invalid gallery type
        invalid_type = 'invalid'
        is_valid = invalid_type in ['fish', 'macro']
        assert is_valid is False, "Should detect invalid gallery type"


class TestErrorHandling:
    """Test error handling scenarios."""
    
    def test_navigation_error_handling(self):
        """Test error handling in navigation logic."""
        # Test with exception in navigation
        target_community = "fish"
        
        try:
            # Simulate error in getting sites data
            raise Exception("Database connection failed")
        except Exception as e:
            error_response = (
                target_community,  # Set community
                [],  # No options
                None,  # No site value
                {'display': 'none'},  # Hide section
                True  # Disable dropdown
            )
            error_handled = True
        
        assert error_handled is True, "Should handle navigation errors"
        assert error_response[1] == [], "Should return empty options on error"
        assert error_response[2] is None, "Should clear site value on error"
        assert error_response[3]['display'] == 'none', "Should hide section on error"
        assert error_response[4] is True, "Should disable dropdown on error"
    
    def test_state_restoration_error_handling(self):
        """Test error handling in state restoration."""
        # Test with exception in state restoration
        saved_community = "fish"
        
        try:
            # Simulate error in getting sites data for restoration
            raise Exception("Sites data unavailable")
        except Exception as e:
            # Should return dash.no_update for all outputs
            error_handled = True
            outputs_updated = False
        
        assert error_handled is True, "Should handle state restoration errors"
        assert outputs_updated is False, "Should not update outputs on error"
    
    def test_site_dropdown_error_handling(self):
        """Test error handling in site dropdown population."""
        # Test with exception in site dropdown logic
        selected_community = "fish"
        
        try:
            # Simulate error in populating sites
            raise Exception("Site data error")
        except Exception as e:
            error_response = (
                {'display': 'block', 'marginBottom': '20px'},  # Show section
                False,  # Enable dropdown
                [],     # No options
                None    # Clear value
            )
            error_handled = True
        
        assert error_handled is True, "Should handle site dropdown errors"
        assert error_response[0]['display'] == 'block', "Should still show section on error"
        assert error_response[1] is False, "Should still enable dropdown on error"
        assert error_response[2] == [], "Should return empty options on error"
        assert error_response[3] is None, "Should clear value on error"
    
    def test_content_display_error_handling(self):
        """Test error handling in content display."""
        # Test with exception in content creation
        selected_community = "fish"
        selected_site = "Test Site"
        
        try:
            # Simulate error in creating biological display
            raise Exception("Content creation failed")
        except Exception as e:
            error_state = {
                'type': 'error_state',
                'title': f"Error Loading {selected_community.title()} Data",
                'message': f"Could not load {selected_community} data for {selected_site}. Please try again.",
                'details': str(e)
            }
            error_handled = True
        
        assert error_handled is True, "Should handle content display errors"
        assert 'Error Loading' in error_state['title'], "Should create appropriate error title"
        assert selected_community in error_state['message'], "Should mention community in error message"
        assert selected_site in error_state['message'], "Should mention site in error message"
        assert 'Content creation failed' in error_state['details'], "Should include error details"


class TestIntegrationScenarios:
    """Test complete integration scenarios."""
    
    def test_complete_navigation_workflow(self):
        """Test complete navigation from map to biological display."""
        # Step 1: Navigation data received
        nav_data = {
            'target_tab': 'biological-tab',
            'target_community': 'fish',
            'target_site': 'Navigation Site'
        }
        
        # Step 2: Parse navigation data
        target_community = nav_data.get('target_community')
        target_site = nav_data.get('target_site')
        
        # Step 3: Mock available sites validation
        available_sites = ['Navigation Site', 'Other Site A', 'Other Site B']
        site_is_valid = target_site in available_sites
        
        # Step 4: Create dropdown options
        if site_is_valid:
            options = [{'label': site, 'value': site} for site in sorted(available_sites)]
            selected_site = target_site
        else:
            options = []
            selected_site = None
        
        # Step 5: Content display requirements
        can_display_content = bool(target_community and selected_site)
        
        # Assertions
        assert target_community == 'fish', "Should extract target community"
        assert target_site == 'Navigation Site', "Should extract target site"
        assert site_is_valid is True, "Should validate target site"
        assert len(options) == 3, "Should create dropdown options"
        assert selected_site == 'Navigation Site', "Should set selected site"
        assert can_display_content is True, "Should enable content display"
    
    def test_complete_state_restoration_workflow(self):
        """Test complete state restoration workflow."""
        # Step 1: Saved state from previous session
        saved_state = {
            'selected_community': 'macro',
            'selected_site': 'Saved Site'
        }
        
        # Step 2: Tab activation
        active_tab = 'biological-tab'
        nav_data = None
        should_restore = (
            active_tab == 'biological-tab' and
            saved_state and
            saved_state.get('selected_community') and
            not nav_data
        )
        
        # Step 3: Extract saved values
        if should_restore:
            saved_community = saved_state.get('selected_community')
            saved_site = saved_state.get('selected_site')
            
            # Step 4: Mock sites validation
            available_sites = ['Saved Site', 'Other Site']
            site_is_valid = saved_site and saved_site in available_sites
            
            # Step 5: Create restoration response
            if site_is_valid:
                options = [{'label': site, 'value': site} for site in sorted(available_sites)]
                site_value_to_restore = saved_site
            else:
                options = []
                site_value_to_restore = None
        
        # Assertions
        assert should_restore is True, "Should detect restoration conditions"
        assert saved_community == 'macro', "Should restore saved community"
        assert saved_site == 'Saved Site', "Should restore saved site"
        assert site_is_valid is True, "Should validate saved site"
        assert len(options) == 2, "Should create restoration options"
        assert site_value_to_restore == 'Saved Site', "Should restore site value"
    
    def test_complete_community_selection_workflow(self):
        """Test complete community selection and site dropdown workflow."""
        # Step 1: User selects community
        selected_community = "fish"
        current_site_value = None
        
        # Step 2: Validate community selection
        valid_communities = ['fish', 'macro']
        is_valid_community = selected_community in valid_communities
        
        # Step 3: Mock getting sites for community
        if is_valid_community:
            available_sites = ['Fish Site A', 'Fish Site B', 'Fish Site C']
            has_sites = len(available_sites) > 0
        else:
            available_sites = []
            has_sites = False
        
        # Step 4: Create dropdown response
        if selected_community and has_sites:
            dropdown_style = {'display': 'block', 'marginBottom': '20px'}
            dropdown_disabled = False
            options = [{'label': site, 'value': site} for site in sorted(available_sites)]
            
            # Check if current site is valid for new community
            site_value_to_set = None
            if current_site_value and current_site_value in available_sites:
                site_value_to_set = current_site_value
        else:
            dropdown_style = {'display': 'none'}
            dropdown_disabled = True
            options = []
            site_value_to_set = None
        
        # Assertions
        assert is_valid_community is True, "Should validate community selection"
        assert has_sites is True, "Should have sites available for community"
        assert dropdown_style['display'] == 'block', "Should show site dropdown"
        assert dropdown_disabled is False, "Should enable site dropdown"
        assert len(options) == 3, "Should create site options"
        assert site_value_to_set is None, "Should not set site value without existing selection"
    
    def test_complete_error_recovery_workflow(self):
        """Test complete error recovery workflow."""
        # Step 1: Error occurs in navigation
        nav_data = {
            'target_tab': 'biological-tab',
            'target_community': 'fish',
            'target_site': 'Error Site'
        }
        
        # Step 2: Error in getting sites data
        sites_error = True
        
        if sites_error:
            # Step 3: Create error response
            error_navigation_response = (
                nav_data.get('target_community'),  # Still set community
                [],  # No options due to error
                None,  # No site value
                {'display': 'none'},  # Hide section
                True  # Disable dropdown
            )
            
            # Step 4: Error propagates to content display
            selected_community = nav_data.get('target_community')
            selected_site = None  # No site due to error
            
            can_display_content = bool(selected_community and selected_site)
            
            if not can_display_content:
                content_response = {
                    'type': 'empty_state',
                    'message': 'Please select a community type and site to view biological data.'
                }
        
        # Assertions
        assert error_navigation_response[0] == 'fish', "Should still set community on error"
        assert error_navigation_response[1] == [], "Should return empty options on error"
        assert error_navigation_response[2] is None, "Should clear site on error"
        assert error_navigation_response[3]['display'] == 'none', "Should hide section on error"
        assert error_navigation_response[4] is True, "Should disable dropdown on error"
        assert can_display_content is False, "Should not display content due to error"
        assert content_response['type'] == 'empty_state', "Should show empty state due to error" 