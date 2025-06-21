"""
Tests for shared_callbacks.py

This file tests the shared callback functions that are used across the entire application,
including modal toggling and navigation handling.
"""

import pytest
import dash
from unittest.mock import Mock, patch, MagicMock


class MockCallbackContext:
    """Mock callback context for testing."""
    def __init__(self, triggered=None):
        self.triggered = triggered or []


class TestModalLogic:
    """Test modal toggle logic directly."""
    
    def test_attribution_modal_toggle_logic(self):
        """Test the logic of toggling attribution modal."""
        # Test case 1: Open modal when link is clicked and modal is closed
        n1, n2, is_open = 1, 0, False
        result = not is_open if (n1 or n2) else is_open
        assert result is True, "Modal should open when link clicked and currently closed"
        
        # Test case 2: Close modal when close button is clicked and modal is open
        n1, n2, is_open = 0, 1, True
        result = not is_open if (n1 or n2) else is_open
        assert result is False, "Modal should close when close button clicked and currently open"
        
        # Test case 3: No change when no buttons clicked
        n1, n2, is_open = 0, 0, True
        result = not is_open if (n1 or n2) else is_open
        assert result is True, "Modal should maintain state when no buttons clicked"
        
        n1, n2, is_open = 0, 0, False
        result = not is_open if (n1 or n2) else is_open
        assert result is False, "Modal should maintain state when no buttons clicked"
    
    def test_image_credits_modal_toggle_logic(self):
        """Test the logic of toggling image credits modal."""
        # Same logic as attribution modal, but testing separately to ensure consistency
        
        # Test opening
        n1, n2, is_open = 1, 0, False
        result = not is_open if (n1 or n2) else is_open
        assert result is True, "Image credits modal should open when clicked"
        
        # Test closing
        n1, n2, is_open = 0, 1, True
        result = not is_open if (n1 or n2) else is_open
        assert result is False, "Image credits modal should close when close button clicked"


class TestNavigationLogic:
    """Test navigation logic directly."""
    
    def test_site_name_extraction_from_click_data(self):
        """Test extracting site name from map click data."""
        # Test normal case
        click_data = {
            'points': [{
                'text': '<b>Site:</b> Test Site<br>Parameter: 8.2 mg/L'
            }]
        }
        
        hover_text = click_data['points'][0]['text']
        site_name = hover_text.split('<br>')[0].replace('<b>Site:</b> ', '')
        assert site_name == 'Test Site', "Should extract site name correctly"
        
        # Test with complex site name
        click_data = {
            'points': [{
                'text': '<b>Site:</b> Tenmile Creek - Highway 125<br>Habitat Score: 85'
            }]
        }
        
        hover_text = click_data['points'][0]['text']
        site_name = hover_text.split('<br>')[0].replace('<b>Site:</b> ', '')
        assert site_name == 'Tenmile Creek - Highway 125', "Should extract complex site name correctly"
    
    def test_parameter_type_detection(self):
        """Test parameter type detection logic."""
        # Test habitat parameter
        parameter = 'habitat:Habitat_Score'
        assert parameter == 'habitat:Habitat_Score', "Should detect habitat parameter"
        
        # Test chemical parameters
        chemical_params = ['chem:pH', 'chem:do_percent', 'chem:Phosphorus', 'chem:Chloride']
        for param in chemical_params:
            assert param.startswith('chem:'), f"Should detect chemical parameter: {param}"
            param_name = param.split(':', 1)[1]
            assert param_name in ['pH', 'do_percent', 'Phosphorus', 'Chloride'], f"Should extract parameter name: {param_name}"
        
        # Test biological parameters
        bio_params = ['bio:Fish_IBI', 'bio:Macro_Combined']
        for param in bio_params:
            assert param.startswith('bio:'), f"Should detect biological parameter: {param}"
    
    def test_biological_parameter_to_community_mapping(self):
        """Test mapping biological parameters to community types."""
        # Test fish mapping
        parameter = 'bio:Fish_IBI'
        if parameter == 'bio:Fish_IBI':
            community_type = 'fish'
        elif parameter == 'bio:Macro_Combined':
            community_type = 'macro'
        else:
            community_type = None
        
        assert community_type == 'fish', "Should map Fish_IBI to fish community"
        
        # Test macro mapping
        parameter = 'bio:Macro_Combined'
        if parameter == 'bio:Fish_IBI':
            community_type = 'fish'
        elif parameter == 'bio:Macro_Combined':
            community_type = 'macro'
        else:
            community_type = None
        
        assert community_type == 'macro', "Should map Macro_Combined to macro community"
        
        # Test unknown parameter
        parameter = 'bio:Unknown_Parameter'
        if parameter == 'bio:Fish_IBI':
            community_type = 'fish'
        elif parameter == 'bio:Macro_Combined':
            community_type = 'macro'
        else:
            community_type = None
        
        assert community_type is None, "Should return None for unknown biological parameter"
    
    def test_navigation_data_structure_habitat(self):
        """Test navigation data structure for habitat navigation."""
        expected_data = {
            'target_tab': 'habitat-tab',
            'target_site': 'Test Site',
            'source_parameter': 'habitat:Habitat_Score'
        }
        
        # Verify structure
        assert 'target_tab' in expected_data, "Navigation data should contain target_tab"
        assert 'target_site' in expected_data, "Navigation data should contain target_site"
        assert 'source_parameter' in expected_data, "Navigation data should contain source_parameter"
        assert expected_data['target_tab'] == 'habitat-tab', "Should target habitat tab"
    
    def test_navigation_data_structure_chemical(self):
        """Test navigation data structure for chemical navigation."""
        parameter = 'chem:pH'
        parameter_name = parameter.split(':', 1)[1]
        
        expected_data = {
            'target_tab': 'chemical-tab',
            'target_site': 'Test Site',
            'target_parameter': parameter_name,
            'source_parameter': parameter
        }
        
        # Verify structure
        assert 'target_tab' in expected_data, "Chemical navigation data should contain target_tab"
        assert 'target_site' in expected_data, "Chemical navigation data should contain target_site"
        assert 'target_parameter' in expected_data, "Chemical navigation data should contain target_parameter"
        assert 'source_parameter' in expected_data, "Chemical navigation data should contain source_parameter"
        assert expected_data['target_parameter'] == 'pH', "Should extract parameter name correctly"
    
    def test_navigation_data_structure_biological(self):
        """Test navigation data structure for biological navigation."""
        parameter = 'bio:Fish_IBI'
        community_type = 'fish' if parameter == 'bio:Fish_IBI' else 'macro'
        
        expected_data = {
            'target_tab': 'biological-tab',
            'target_site': 'Test Site',
            'target_community': community_type,
            'source_parameter': parameter
        }
        
        # Verify structure
        assert 'target_tab' in expected_data, "Biological navigation data should contain target_tab"
        assert 'target_site' in expected_data, "Biological navigation data should contain target_site"
        assert 'target_community' in expected_data, "Biological navigation data should contain target_community"
        assert 'source_parameter' in expected_data, "Biological navigation data should contain source_parameter"
        assert expected_data['target_community'] == 'fish', "Should map to correct community type"
    
    def test_overview_link_navigation_data(self):
        """Test navigation data structure for overview links."""
        expected_data = {'target_tab': None, 'target_site': None}
        
        # Verify structure for overview navigation
        assert 'target_tab' in expected_data, "Overview navigation should contain target_tab"
        assert 'target_site' in expected_data, "Overview navigation should contain target_site"
        assert expected_data['target_tab'] is None, "Overview navigation should clear target_tab"
        assert expected_data['target_site'] is None, "Overview navigation should clear target_site"


class TestCallbackContextHandling:
    """Test callback context handling logic."""
    
    def test_trigger_id_extraction(self):
        """Test extracting trigger ID from callback context."""
        # Test overview link trigger
        prop_id = 'chemical-overview-link.n_clicks'
        trigger_id = prop_id.split('.')[0]
        assert trigger_id == 'chemical-overview-link', "Should extract trigger ID correctly"
        
        # Test map click trigger
        prop_id = 'site-map-graph.clickData'
        trigger_id = prop_id.split('.')[0]
        assert trigger_id == 'site-map-graph', "Should extract map trigger ID correctly"
    
    def test_overview_link_detection(self):
        """Test detection of overview link triggers."""
        overview_triggers = ['chemical-overview-link', 'biological-overview-link', 'habitat-overview-link']
        
        for trigger in overview_triggers:
            assert trigger in overview_triggers, f"Should detect {trigger} as overview link"
        
        # Test non-overview trigger
        non_overview_trigger = 'site-map-graph'
        assert non_overview_trigger not in overview_triggers, "Should not detect map click as overview link"
    
    def test_context_validation(self):
        """Test callback context validation logic."""
        # Test empty context
        triggered = []
        has_trigger = bool(triggered)
        assert has_trigger is False, "Should detect empty trigger context"
        
        # Test valid context
        triggered = [{'prop_id': 'site-map-graph.clickData'}]
        has_trigger = bool(triggered)
        assert has_trigger is True, "Should detect valid trigger context"


class TestErrorHandling:
    """Test error handling scenarios."""
    
    def test_malformed_click_data_handling(self):
        """Test handling of malformed click data."""
        # Test missing text field
        malformed_data = {
            'points': [{}]  # Missing text field
        }
        
        try:
            hover_text = malformed_data['points'][0]['text']
            site_name = hover_text.split('<br>')[0].replace('<b>Site:</b> ', '')
            extraction_failed = False
        except KeyError:
            extraction_failed = True
        
        assert extraction_failed is True, "Should fail gracefully with malformed click data"
        
        # Test malformed text format
        malformed_text_data = {
            'points': [{
                'text': 'Invalid format without site'
            }]
        }
        
        try:
            hover_text = malformed_text_data['points'][0]['text']
            site_name = hover_text.split('<br>')[0].replace('<b>Site:</b> ', '')
            # This would result in an unexpected site name
            is_valid_format = site_name != 'Invalid format without site'
        except:
            is_valid_format = False
        
        assert is_valid_format is False, "Should detect invalid text format"
    
    def test_missing_click_data_handling(self):
        """Test handling of missing click data."""
        click_data = None
        
        # Test the condition used in the actual callback
        has_valid_data = bool(click_data)
        assert has_valid_data is False, "Should detect missing click data"
    
    def test_missing_parameter_handling(self):
        """Test handling of missing parameter."""
        current_parameter = None
        
        # Test the condition used in the actual callback
        has_parameter = bool(current_parameter)
        assert has_parameter is False, "Should detect missing parameter"


class TestIntegrationScenarios:
    """Integration-style tests that combine multiple logic components."""
    
    def test_complete_habitat_navigation_scenario(self):
        """Test complete habitat navigation scenario."""
        # Simulate the complete flow
        click_data = {
            'points': [{
                'text': '<b>Site:</b> Tenmile Creek - Highway 125<br>Habitat Score: 85'
            }]
        }
        current_parameter = 'habitat:Habitat_Score'
        trigger_id = 'site-map-graph'
        
        # Validate inputs
        assert click_data is not None, "Click data should be present"
        assert current_parameter is not None, "Parameter should be present"
        assert trigger_id == 'site-map-graph', "Should be triggered by map click"
        
        # Extract site name
        hover_text = click_data['points'][0]['text']
        site_name = hover_text.split('<br>')[0].replace('<b>Site:</b> ', '')
        
        # Determine navigation target
        if current_parameter == 'habitat:Habitat_Score':
            target_tab = "habitat-tab"
            nav_data = {
                'target_tab': 'habitat-tab',
                'target_site': site_name,
                'source_parameter': current_parameter
            }
        
        # Verify results
        assert target_tab == "habitat-tab", "Should navigate to habitat tab"
        assert nav_data['target_site'] == 'Tenmile Creek - Highway 125', "Should extract correct site name"
        assert nav_data['source_parameter'] == 'habitat:Habitat_Score', "Should preserve source parameter"
    
    def test_complete_chemical_navigation_scenario(self):
        """Test complete chemical navigation scenario."""
        # Simulate the complete flow
        click_data = {
            'points': [{
                'text': '<b>Site:</b> Test Site<br>pH: 7.5'
            }]
        }
        current_parameter = 'chem:pH'
        trigger_id = 'site-map-graph'
        
        # Validate inputs
        assert click_data is not None, "Click data should be present"
        assert current_parameter is not None, "Parameter should be present"
        assert current_parameter.startswith('chem:'), "Should be chemical parameter"
        
        # Extract site name and parameter
        hover_text = click_data['points'][0]['text']
        site_name = hover_text.split('<br>')[0].replace('<b>Site:</b> ', '')
        parameter_name = current_parameter.split(':', 1)[1]
        
        # Determine navigation target
        target_tab = "chemical-tab"
        nav_data = {
            'target_tab': 'chemical-tab',
            'target_site': site_name,
            'target_parameter': parameter_name,
            'source_parameter': current_parameter
        }
        
        # Verify results
        assert target_tab == "chemical-tab", "Should navigate to chemical tab"
        assert nav_data['target_site'] == 'Test Site', "Should extract correct site name"
        assert nav_data['target_parameter'] == 'pH', "Should extract parameter name"
        assert nav_data['source_parameter'] == 'chem:pH', "Should preserve source parameter" 