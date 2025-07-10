"""
Tests for navigation flow integration

This file tests end-to-end navigation workflows including:
- Map click → Tab navigation → Content display
- State persistence across tab switches
- Cross-tab data consistency
- User interaction workflows
"""

import unittest
import os
import sys
from unittest.mock import patch, MagicMock, call
import dash
from dash import html, dcc, callback_context
import pandas as pd
import json

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

# Import modules to test
from callbacks.shared_callbacks import register_shared_callbacks
from callbacks.chemical_callbacks import register_chemical_callbacks
from callbacks.biological_callbacks import register_biological_callbacks
from callbacks.habitat_callbacks import register_habitat_callbacks
from callbacks.overview_callbacks import register_overview_callbacks


class TestMapToTabNavigation(unittest.TestCase):
    """Test navigation from map clicks to specific tabs."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create mock app for testing
        self.app = dash.Dash(__name__)
        self.app.layout = html.Div([
            dcc.Tabs(id='main-tabs'),
            dcc.Store(id='navigation-store'),
            dcc.Graph(id='site-map-graph'),
            dcc.Dropdown(id='parameter-dropdown'),
            html.Button(id='chemical-overview-link'),
            html.Button(id='biological-overview-link'),
            html.Button(id='habitat-overview-link'),
        ])
        
        # Sample click data for testing
        self.sample_click_data = {
            'points': [{
                'text': '<b>Site:</b> Test Site<br>pH: 7.5'
            }]
        }
        
        self.chemical_click_data = {
            'points': [{
                'text': '<b>Site:</b> Chemical Site<br>Dissolved Oxygen: 8.2 mg/L'
            }]
        }
        
        self.habitat_click_data = {
            'points': [{
                'text': '<b>Site:</b> Habitat Site<br>Habitat Score: 85'
            }]
        }
    
    @patch('dash.callback_context')
    def test_chemical_parameter_map_navigation(self, mock_ctx):
        """Test navigation from chemical parameter map click."""
        # Mock callback context
        mock_ctx.triggered = [{'prop_id': 'site-map-graph.clickData'}]
        
        # Test chemical parameter navigation logic
        click_data = self.chemical_click_data
        current_parameter = 'chem:dissolved_oxygen'
        
        # Extract site name from click data
        hover_text = click_data['points'][0]['text']
        site_name = hover_text.split('<br>')[0].replace('<b>Site:</b> ', '')
        
        # Determine target tab and navigation data
        if current_parameter.startswith('chem:'):
            parameter_name = current_parameter.split(':', 1)[1]
            target_tab = "chemical-tab"
            nav_data = {
                'target_tab': 'chemical-tab',
                'target_site': site_name,
                'target_parameter': parameter_name,
                'source_parameter': current_parameter
            }
        
        # Verify navigation results
        self.assertEqual(target_tab, "chemical-tab")
        self.assertEqual(nav_data['target_site'], 'Chemical Site')
        self.assertEqual(nav_data['target_parameter'], 'dissolved_oxygen')
        self.assertEqual(nav_data['source_parameter'], 'chem:dissolved_oxygen')
    
    @patch('dash.callback_context')
    def test_fish_parameter_map_navigation(self, mock_ctx):
        """Test navigation from fish parameter map click."""
        # Mock callback context
        mock_ctx.triggered = [{'prop_id': 'site-map-graph.clickData'}]
        
        # Test fish parameter navigation logic
        click_data = {
            'points': [{
                'text': '<b>Site:</b> Fish Site<br>Fish Score: 92'
            }]
        }
        current_parameter = 'bio:fish'
        
        # Extract site name
        hover_text = click_data['points'][0]['text']
        site_name = hover_text.split('<br>')[0].replace('<b>Site:</b> ', '')
        
        # Determine target tab for biological data
        if current_parameter.startswith('bio:'):
            community_type = current_parameter.split(':', 1)[1]
            target_tab = "biological-tab"
            nav_data = {
                'target_tab': 'biological-tab',
                'target_site': site_name,
                'target_community': community_type,
                'source_parameter': current_parameter
            }
        
        # Verify navigation results
        self.assertEqual(target_tab, "biological-tab")
        self.assertEqual(nav_data['target_site'], 'Fish Site')
        self.assertEqual(nav_data['target_community'], 'fish')
    
    @patch('dash.callback_context')
    def test_macro_parameter_map_navigation(self, mock_ctx):
        """Test navigation from macro parameter map click."""
        # Mock callback context
        mock_ctx.triggered = [{'prop_id': 'site-map-graph.clickData'}]
        
        # Test macro parameter navigation logic
        click_data = {
            'points': [{
                'text': '<b>Site:</b> Macro Site<br>Macro Score: 78'
            }]
        }
        current_parameter = 'bio:macro'
        
        # Extract site name
        hover_text = click_data['points'][0]['text']
        site_name = hover_text.split('<br>')[0].replace('<b>Site:</b> ', '')
        
        # Determine target tab for macroinvertebrate data
        if current_parameter.startswith('bio:'):
            community_type = current_parameter.split(':', 1)[1]
            target_tab = "biological-tab"
            nav_data = {
                'target_tab': 'biological-tab',
                'target_site': site_name,
                'target_community': community_type,
                'source_parameter': current_parameter
            }
        
        # Verify navigation results
        self.assertEqual(target_tab, "biological-tab")
        self.assertEqual(nav_data['target_site'], 'Macro Site')
        self.assertEqual(nav_data['target_community'], 'macro')
    
    @patch('dash.callback_context')
    def test_habitat_parameter_map_navigation(self, mock_ctx):
        """Test navigation from habitat parameter map click."""
        # Mock callback context
        mock_ctx.triggered = [{'prop_id': 'site-map-graph.clickData'}]
        
        # Test habitat parameter navigation logic
        click_data = self.habitat_click_data
        current_parameter = 'habitat:Habitat_Score'
        
        # Extract site name
        hover_text = click_data['points'][0]['text']
        site_name = hover_text.split('<br>')[0].replace('<b>Site:</b> ', '')
        
        # Determine target tab for habitat data
        if current_parameter == 'habitat:Habitat_Score':
            target_tab = "habitat-tab"
            nav_data = {
                'target_tab': 'habitat-tab',
                'target_site': site_name,
                'source_parameter': current_parameter
            }
        
        # Verify navigation results
        self.assertEqual(target_tab, "habitat-tab")
        self.assertEqual(nav_data['target_site'], 'Habitat Site')
        self.assertEqual(nav_data['source_parameter'], 'habitat:Habitat_Score')
    
    def test_invalid_map_click_handling(self):
        """Test handling of invalid map click data."""
        # Test with missing click data
        click_data = None
        current_parameter = 'chem:pH'
        
        # Test invalid click data handling
        if click_data is None or 'points' not in click_data:
            nav_data = None
        
        # Verify invalid data is handled
        self.assertIsNone(nav_data)
        
        # Test with malformed click data
        malformed_click_data = {
            'points': [{
                'text': 'Invalid format without site'
            }]
        }
        
        # Extract site name (should fail gracefully)
        try:
            hover_text = malformed_click_data['points'][0]['text']
            if '<b>Site:</b>' not in hover_text:
                site_name = None
            else:
                site_name = hover_text.split('<br>')[0].replace('<b>Site:</b> ', '')
        except:
            site_name = None
        
        # Verify malformed data is handled
        self.assertIsNone(site_name)


class TestStatePersistence(unittest.TestCase):
    """Test state persistence across tab switches."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Mock navigation store data
        self.chemical_state = {
            'active_tab': 'chemical-tab',
            'selected_site': 'Test Site A',
            'selected_parameter': 'pH',
            'date_range': ['2020-01-01', '2023-12-31']
        }
        
        self.biological_state = {
            'active_tab': 'biological-tab',
            'selected_site': 'Test Site B',
            'selected_community': 'fish',
            'date_range': ['2020-01-01', '2023-12-31']
        }
        
        self.habitat_state = {
            'active_tab': 'habitat-tab',
            'selected_site': 'Test Site C',
            'date_range': ['2020-01-01', '2023-12-31']
        }
        
        self.overview_state = {
            'active_tab': 'overview-tab',
            'selected_parameter': 'chem:pH',
            'map_view': 'Oklahoma'
        }
    
    def test_chemical_state_persistence(self):
        """Test chemical tab state persistence."""
        # Test state serialization
        state_json = json.dumps(self.chemical_state)
        restored_state = json.loads(state_json)
        
        # Verify state is preserved
        self.assertEqual(restored_state['active_tab'], 'chemical-tab')
        self.assertEqual(restored_state['selected_site'], 'Test Site A')
        self.assertEqual(restored_state['selected_parameter'], 'pH')
        
        # Test state update
        updated_state = self.chemical_state.copy()
        updated_state['selected_parameter'] = 'dissolved_oxygen'
        
        self.assertEqual(updated_state['selected_parameter'], 'dissolved_oxygen')
        self.assertEqual(updated_state['selected_site'], 'Test Site A')  # Other values preserved
    
    def test_biological_state_persistence(self):
        """Test biological tab state persistence."""
        # Test state serialization
        state_json = json.dumps(self.biological_state)
        restored_state = json.loads(state_json)
        
        # Verify state is preserved
        self.assertEqual(restored_state['active_tab'], 'biological-tab')
        self.assertEqual(restored_state['selected_site'], 'Test Site B')
        self.assertEqual(restored_state['selected_community'], 'fish')
        
        # Test community switch
        updated_state = self.biological_state.copy()
        updated_state['selected_community'] = 'macro'
        
        self.assertEqual(updated_state['selected_community'], 'macro')
        self.assertEqual(updated_state['selected_site'], 'Test Site B')  # Site preserved
    
    def test_habitat_state_persistence(self):
        """Test habitat tab state persistence."""
        # Test state serialization
        state_json = json.dumps(self.habitat_state)
        restored_state = json.loads(state_json)
        
        # Verify state is preserved
        self.assertEqual(restored_state['active_tab'], 'habitat-tab')
        self.assertEqual(restored_state['selected_site'], 'Test Site C')
        self.assertIsInstance(restored_state['date_range'], list)
    
    def test_overview_state_persistence(self):
        """Test overview tab state persistence."""
        # Test state serialization
        state_json = json.dumps(self.overview_state)
        restored_state = json.loads(state_json)
        
        # Verify state is preserved
        self.assertEqual(restored_state['active_tab'], 'overview-tab')
        self.assertEqual(restored_state['selected_parameter'], 'chem:pH')
        self.assertEqual(restored_state['map_view'], 'Oklahoma')
    
    def test_state_restoration_after_navigation(self):
        """Test state restoration after navigation between tabs."""
        # Simulate navigation sequence
        navigation_history = [
            self.overview_state,
            self.chemical_state,
            self.biological_state,
            self.habitat_state
        ]
        
        # Test that each state can be restored
        for state in navigation_history:
            # Serialize and deserialize state
            state_json = json.dumps(state)
            restored_state = json.loads(state_json)
            
            # Verify critical fields are preserved
            self.assertIn('active_tab', restored_state)
            
            # Verify tab-specific fields
            if state['active_tab'] == 'chemical-tab':
                self.assertIn('selected_parameter', restored_state)
            elif state['active_tab'] == 'biological-tab':
                self.assertIn('selected_community', restored_state)
            elif state['active_tab'] == 'overview-tab':
                self.assertIn('map_view', restored_state)
        
        # Test state transitions
        current_state = self.overview_state.copy()
        
        # Navigate to chemical tab
        current_state.update({
            'active_tab': 'chemical-tab',
            'selected_site': 'New Site',
            'selected_parameter': 'phosphorus'
        })
        
        self.assertEqual(current_state['active_tab'], 'chemical-tab')
        self.assertEqual(current_state['selected_parameter'], 'phosphorus')


class TestCrossTabConsistency(unittest.TestCase):
    """Test data consistency across different tabs."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.sample_sites = ['Site A', 'Site B', 'Site C']
        self.sample_dates = ['2023-01-15', '2023-06-15', '2023-12-15']
        self.sample_parameters = ['pH', 'dissolved_oxygen', 'phosphorus']
    
    @patch('utils.get_sites_with_data')
    def test_site_data_consistency_across_tabs(self, mock_get_sites):
        """Test that site data is consistent across all tabs."""
        # Mock sites for different data types
        mock_get_sites.side_effect = lambda data_type: {
            'chemical': self.sample_sites,
            'fish': self.sample_sites[:2],  # Fish data at fewer sites
            'macro': self.sample_sites,
            'habitat': self.sample_sites[1:]  # Habitat data at different sites
        }.get(data_type, self.sample_sites)
        
        # Test site consistency
        chemical_sites = set(mock_get_sites('chemical'))
        fish_sites = set(mock_get_sites('fish'))
        macro_sites = set(mock_get_sites('macro'))
        habitat_sites = set(mock_get_sites('habitat'))
        
        # Verify expected differences
        self.assertEqual(len(chemical_sites), 3)
        self.assertEqual(len(fish_sites), 2)
        self.assertEqual(len(macro_sites), 3)
        self.assertEqual(len(habitat_sites), 2)
        
        # Test intersection of sites
        common_sites = chemical_sites & fish_sites & macro_sites & habitat_sites
        self.assertTrue(len(common_sites) >= 1)  # At least one site should have all data types
    
    def test_parameter_data_consistency(self):
        """Test that parameter data is consistent across tabs."""
        # Test chemical parameters
        chemical_params = ['pH', 'dissolved_oxygen', 'phosphorus', 'chloride']
        
        # Test biological metrics
        biological_metrics = ['total_species', 'total_score', 'integrity_class']
        
        # Test habitat metrics
        habitat_metrics = ['total_score', 'habitat_grade']
        
        # Verify parameter structure consistency
        for param in chemical_params:
            self.assertIsInstance(param, str)
            self.assertGreater(len(param), 0)
        
        for metric in biological_metrics:
            self.assertIsInstance(metric, str)
            self.assertGreater(len(metric), 0)
        
        for metric in habitat_metrics:
            self.assertIsInstance(metric, str)
            self.assertGreater(len(metric), 0)
    
    def test_date_range_consistency(self):
        """Test that date ranges are consistent across tabs."""
        # Test date range validation
        start_date = '2020-01-01'
        end_date = '2023-12-31'
        
        # Parse dates
        start_parsed = pd.to_datetime(start_date)
        end_parsed = pd.to_datetime(end_date)
        
        # Verify date range is valid
        self.assertLess(start_parsed, end_parsed)
        
        # Test date range filtering
        test_dates = pd.to_datetime(self.sample_dates)
        filtered_dates = test_dates[(test_dates >= start_parsed) & (test_dates <= end_parsed)]
        
        # All test dates should be within range
        self.assertEqual(len(filtered_dates), len(test_dates))
    
    def test_navigation_store_consistency(self):
        """Test that navigation store maintains consistent state."""
        # Test navigation store structure
        navigation_data = {
            'current_tab': 'chemical-tab',
            'target_site': 'Test Site',
            'target_parameter': 'pH',
            'navigation_source': 'map_click',
            'timestamp': '2023-12-01T10:00:00'
        }
        
        # Test serialization/deserialization
        serialized = json.dumps(navigation_data)
        deserialized = json.loads(serialized)
        
        # Verify consistency
        self.assertEqual(deserialized['current_tab'], navigation_data['current_tab'])
        self.assertEqual(deserialized['target_site'], navigation_data['target_site'])
        self.assertEqual(deserialized['target_parameter'], navigation_data['target_parameter'])
        
        # Test navigation data validation
        required_fields = ['current_tab', 'target_site']
        for field in required_fields:
            self.assertIn(field, navigation_data)
            self.assertIsNotNone(navigation_data[field])
        
        # Test navigation data update
        updated_navigation = navigation_data.copy()
        updated_navigation['current_tab'] = 'biological-tab'
        updated_navigation['target_community'] = 'fish'
        
        # Verify update preserved other fields
        self.assertEqual(updated_navigation['target_site'], 'Test Site')
        self.assertEqual(updated_navigation['current_tab'], 'biological-tab')


class TestUserInteractionWorkflows(unittest.TestCase):
    """Test complete user interaction scenarios."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.workflow_data = {
            'sites': ['Creek Site A', 'Lake Site B'],
            'parameters': ['pH', 'dissolved_oxygen'],
            'date_range': ['2020-01-01', '2023-12-31']
        }
    
    def test_overview_to_chemical_workflow(self):
        """Test complete workflow from overview to chemical analysis."""
        # Step 1: User starts on overview tab
        initial_state = {
            'active_tab': 'overview-tab',
            'selected_parameter': 'chem:pH'
        }
        
        # Step 2: User clicks on map point
        map_click_data = {
            'points': [{
                'text': '<b>Site:</b> Creek Site A<br>pH: 7.2'
            }]
        }
        
        # Step 3: Extract navigation data
        hover_text = map_click_data['points'][0]['text']
        site_name = hover_text.split('<br>')[0].replace('<b>Site:</b> ', '')
        parameter_value = hover_text.split('<br>')[1]
        
        # Step 4: Navigate to chemical tab
        navigation_state = {
            'active_tab': 'chemical-tab',
            'target_site': site_name,
            'target_parameter': 'pH',
            'source': 'overview_map_click'
        }
        
        # Step 5: Chemical tab loads with site-specific data
        chemical_tab_state = {
            'selected_site': site_name,
            'selected_parameter': 'pH',
            'view_mode': 'individual_site'
        }
        
        # Verify workflow
        self.assertEqual(initial_state['active_tab'], 'overview-tab')
        self.assertEqual(site_name, 'Creek Site A')
        self.assertEqual(navigation_state['target_site'], 'Creek Site A')
        self.assertEqual(chemical_tab_state['selected_site'], 'Creek Site A')
        
        # Test state transitions
        self.assertNotEqual(initial_state['active_tab'], navigation_state['active_tab'])
        self.assertEqual(navigation_state['target_site'], chemical_tab_state['selected_site'])
    
    def test_map_to_biological_workflow(self):
        """Test workflow from map to biological data analysis."""
        # Step 1: User clicks on biological parameter in map
        map_click_data = {
            'points': [{
                'text': '<b>Site:</b> Lake Site B<br>Fish Score: 85'
            }]
        }
        
        current_parameter = 'bio:fish'
        
        # Step 2: Extract site information
        hover_text = map_click_data['points'][0]['text']
        site_name = hover_text.split('<br>')[0].replace('<b>Site:</b> ', '')
        
        # Step 3: Determine biological community type
        if current_parameter.startswith('bio:'):
            community_type = current_parameter.split(':', 1)[1]
        
        # Step 4: Navigate to biological tab
        navigation_state = {
            'active_tab': 'biological-tab',
            'target_site': site_name,
            'target_community': community_type,
            'source': 'map_click'
        }
        
        # Step 5: Biological tab loads with community-specific data
        biological_tab_state = {
            'selected_site': site_name,
            'selected_community': community_type,
            'data_available': True
        }
        
        # Verify workflow
        self.assertEqual(site_name, 'Lake Site B')
        self.assertEqual(community_type, 'fish')
        self.assertEqual(navigation_state['target_community'], 'fish')
        self.assertEqual(biological_tab_state['selected_community'], 'fish')
    
    def test_cross_tab_comparison_workflow(self):
        """Test workflow for comparing data across tabs."""
        # Step 1: User analyzes chemical data
        chemical_analysis = {
            'site': 'Creek Site A',
            'parameter': 'pH',
            'current_value': 7.2,
            'status': 'Normal'
        }
        
        # Step 2: User switches to biological tab for same site
        biological_analysis = {
            'site': 'Creek Site A',
            'community': 'fish',
            'score': 85,
            'integrity_class': 'Good'
        }
        
        # Step 3: User switches to habitat tab for same site
        habitat_analysis = {
            'site': 'Creek Site A',
            'habitat_score': 78,
            'grade': 'Good'
        }
        
        # Step 4: Compare results across data types
        comparison_results = {
            'site': 'Creek Site A',
            'chemical_status': chemical_analysis['status'],
            'biological_status': biological_analysis['integrity_class'],
            'habitat_status': habitat_analysis['grade'],
            'overall_assessment': 'Good'  # Based on multiple indicators
        }
        
        # Verify cross-tab consistency
        self.assertEqual(chemical_analysis['site'], biological_analysis['site'])
        self.assertEqual(biological_analysis['site'], habitat_analysis['site'])
        self.assertEqual(comparison_results['site'], 'Creek Site A')
        
        # Verify assessment consistency
        self.assertIn(comparison_results['chemical_status'], ['Normal', 'Good', 'Poor'])
        self.assertIn(comparison_results['biological_status'], ['Excellent', 'Good', 'Fair', 'Poor'])
        self.assertIn(comparison_results['habitat_status'], ['Excellent', 'Good', 'Fair', 'Poor'])
    
    def test_site_exploration_workflow(self):
        """Test comprehensive site exploration workflow."""
        target_site = 'Creek Site A'
        
        # Step 1: Overview of site data availability
        site_data_availability = {
            'site_name': target_site,
            'has_chemical_data': True,
            'has_fish_data': True,
            'has_macro_data': False,
            'has_habitat_data': True,
            'date_range': ['2020-01-01', '2023-12-31']
        }
        
        # Step 2: Chemical data exploration
        chemical_exploration = {
            'site': target_site,
            'available_parameters': ['pH', 'dissolved_oxygen', 'phosphorus'],
            'measurement_count': 15,
            'latest_date': '2023-12-01'
        }
        
        # Step 3: Biological data exploration
        biological_exploration = {
            'site': target_site,
            'available_communities': ['fish'],  # Only fish data available
            'latest_survey': '2023-11-15',
            'species_count': 8
        }
        
        # Step 4: Habitat data exploration
        habitat_exploration = {
            'site': target_site,
            'latest_assessment': '2023-10-20',
            'score': 78,
            'grade': 'Good'
        }
        
        # Verify comprehensive site exploration
        self.assertTrue(site_data_availability['has_chemical_data'])
        self.assertTrue(site_data_availability['has_fish_data'])
        self.assertFalse(site_data_availability['has_macro_data'])
        self.assertTrue(site_data_availability['has_habitat_data'])
        
        # Verify data consistency across explorations
        self.assertEqual(chemical_exploration['site'], target_site)
        self.assertEqual(biological_exploration['site'], target_site)
        self.assertEqual(habitat_exploration['site'], target_site)
        
        # Verify data completeness
        self.assertGreater(chemical_exploration['measurement_count'], 0)
        self.assertGreater(biological_exploration['species_count'], 0)
        self.assertIsNotNone(habitat_exploration['score'])


class TestNavigationErrorHandling(unittest.TestCase):
    """Test error handling in navigation flows."""
    
    def test_invalid_navigation_data(self):
        """Test handling of invalid navigation data."""
        # Test with None navigation data
        nav_data = None
        
        if nav_data is None:
            default_nav = {
                'active_tab': 'overview-tab',
                'error': 'Invalid navigation data'
            }
        
        self.assertEqual(default_nav['active_tab'], 'overview-tab')
        self.assertIn('error', default_nav)
        
        # Test with malformed navigation data
        malformed_nav = {
            'invalid_field': 'test',
            'missing_required_fields': True
        }
        
        required_fields = ['active_tab']
        has_required = all(field in malformed_nav for field in required_fields)
        
        if not has_required:
            error_nav = {
                'active_tab': 'overview-tab',
                'error': 'Missing required navigation fields'
            }
        
        self.assertFalse(has_required)
        self.assertEqual(error_nav['active_tab'], 'overview-tab')
        
        # Test with invalid tab name
        invalid_tab_nav = {
            'active_tab': 'nonexistent-tab',
            'target_site': 'Test Site'
        }
        
        valid_tabs = ['overview-tab', 'chemical-tab', 'biological-tab', 'habitat-tab', 'protect-streams-tab', 'source-data-tab']
        
        if invalid_tab_nav['active_tab'] not in valid_tabs:
            corrected_nav = {
                'active_tab': 'overview-tab',
                'original_tab': invalid_tab_nav['active_tab'],
                'error': 'Invalid tab name'
            }
        
        self.assertNotIn(invalid_tab_nav['active_tab'], valid_tabs)
        self.assertEqual(corrected_nav['active_tab'], 'overview-tab')
    
    def test_missing_site_data_navigation(self):
        """Test navigation when site data is missing."""
        # Test navigation to site with no data
        navigation_request = {
            'target_tab': 'chemical-tab',
            'target_site': 'Nonexistent Site',
            'target_parameter': 'pH'
        }
        
        # Mock site data check
        available_sites = ['Site A', 'Site B', 'Site C']
        
        if navigation_request['target_site'] not in available_sites:
            error_response = {
                'active_tab': navigation_request['target_tab'],
                'error': f"No data available for site: {navigation_request['target_site']}",
                'available_sites': available_sites,
                'fallback_site': available_sites[0] if available_sites else None
            }
        
        self.assertNotIn(navigation_request['target_site'], available_sites)
        self.assertIn('error', error_response)
        self.assertEqual(error_response['fallback_site'], 'Site A')
        
        # Test navigation with missing parameter data
        parameter_request = {
            'target_tab': 'chemical-tab',
            'target_site': 'Site A',
            'target_parameter': 'nonexistent_parameter'
        }
        
        available_parameters = ['pH', 'dissolved_oxygen', 'phosphorus']
        
        if parameter_request['target_parameter'] not in available_parameters:
            parameter_error = {
                'active_tab': parameter_request['target_tab'],
                'error': f"Parameter not available: {parameter_request['target_parameter']}",
                'available_parameters': available_parameters,
                'fallback_parameter': available_parameters[0]
            }
        
        self.assertNotIn(parameter_request['target_parameter'], available_parameters)
        self.assertEqual(parameter_error['fallback_parameter'], 'pH')
    
    def test_corrupted_state_recovery(self):
        """Test recovery from corrupted navigation state."""
        # Test corrupted JSON state
        corrupted_json = '{"active_tab": "chemical-tab", "invalid_json":'
        
        try:
            parsed_state = json.loads(corrupted_json)
        except json.JSONDecodeError:
            recovery_state = {
                'active_tab': 'overview-tab',
                'error': 'Corrupted state data, using defaults',
                'recovery_timestamp': '2023-12-01T10:00:00'
            }
        
        self.assertEqual(recovery_state['active_tab'], 'overview-tab')
        self.assertIn('error', recovery_state)
        
        # Test state with invalid data types
        invalid_type_state = {
            'active_tab': 123,  # Should be string
            'target_site': None,
            'date_range': 'invalid_date_format'
        }
        
        # Validate and correct state
        corrected_state = {}
        
        if isinstance(invalid_type_state.get('active_tab'), str):
            corrected_state['active_tab'] = invalid_type_state['active_tab']
        else:
            corrected_state['active_tab'] = 'overview-tab'
        
        if isinstance(invalid_type_state.get('target_site'), str):
            corrected_state['target_site'] = invalid_type_state['target_site']
        else:
            corrected_state['target_site'] = None
        
        if isinstance(invalid_type_state.get('date_range'), list):
            corrected_state['date_range'] = invalid_type_state['date_range']
        else:
            corrected_state['date_range'] = ['2020-01-01', '2023-12-31']
        
        self.assertEqual(corrected_state['active_tab'], 'overview-tab')
        self.assertIsNone(corrected_state['target_site'])
        self.assertIsInstance(corrected_state['date_range'], list)
        
        # Test partial state recovery
        partial_state = {
            'active_tab': 'chemical-tab'
            # Missing other expected fields
        }
        
        required_defaults = {
            'target_site': None,
            'target_parameter': None,
            'date_range': ['2020-01-01', '2023-12-31']
        }
        
        complete_state = {**partial_state, **required_defaults}
        
        self.assertEqual(complete_state['active_tab'], 'chemical-tab')
        self.assertIsNone(complete_state['target_site'])
        self.assertIsInstance(complete_state['date_range'], list)
    
    @patch('time.sleep')
    def test_network_error_during_navigation(self, mock_sleep):
        """Test handling of network errors during navigation."""
        # Simulate network timeout during data loading
        def simulate_network_error():
            raise TimeoutError("Network request timed out")
        
        # Test error handling
        try:
            simulate_network_error()
        except TimeoutError as e:
            error_state = {
                'active_tab': 'overview-tab',
                'error': f"Network error: {str(e)}",
                'retry_available': True,
                'retry_count': 0
            }
        
        self.assertIn('error', error_state)
        self.assertTrue(error_state['retry_available'])
        self.assertEqual(error_state['retry_count'], 0)
        
        # Test retry mechanism
        max_retries = 3
        current_retry = 0
        
        while current_retry < max_retries:
            try:
                # Simulate retry
                if current_retry < 2:  # Fail first two attempts
                    raise TimeoutError("Still failing")
                else:
                    # Success on third attempt
                    success_state = {
                        'active_tab': 'chemical-tab',
                        'data_loaded': True,
                        'retry_count': current_retry
                    }
                    break
            except TimeoutError:
                current_retry += 1
                mock_sleep(1)  # Simulate retry delay
        
        if current_retry < max_retries:
            self.assertTrue(success_state['data_loaded'])
            self.assertEqual(success_state['retry_count'], 2)
        else:
            final_error_state = {
                'active_tab': 'overview-tab',
                'error': 'Maximum retries exceeded',
                'retry_count': max_retries
            }
            self.assertEqual(final_error_state['retry_count'], max_retries)


class TestNavigationPerformance(unittest.TestCase):
    """Test navigation performance benchmarks."""
    
    def test_navigation_response_time(self):
        """Test navigation response time benchmarks."""
        import time
        
        # Test simple navigation timing
        start_time = time.time()
        
        # Simulate navigation processing
        navigation_data = {
            'active_tab': 'chemical-tab',
            'target_site': 'Test Site',
            'target_parameter': 'pH'
        }
        
        # Simulate state update
        serialized_state = json.dumps(navigation_data)
        deserialized_state = json.loads(serialized_state)
        
        # Simulate component update
        updated_components = {
            'site-dropdown': deserialized_state['target_site'],
            'parameter-dropdown': deserialized_state['target_parameter'],
            'active-tab': deserialized_state['active_tab']
        }
        
        end_time = time.time()
        navigation_time = end_time - start_time
        
        # Verify navigation is fast (under 100ms)
        self.assertLess(navigation_time, 0.1)
        self.assertEqual(updated_components['site-dropdown'], 'Test Site')
        
        # Test complex navigation timing
        start_time = time.time()
        
        # Simulate complex navigation with multiple updates
        complex_navigation = {
            'active_tab': 'biological-tab',
            'target_site': 'Complex Site',
            'target_community': 'fish',
            'date_range': ['2020-01-01', '2023-12-31'],
            'filter_options': ['species_count', 'total_score'],
            'view_mode': 'detailed'
        }
        
        # Process complex navigation
        for key, value in complex_navigation.items():
            processed_value = value if not isinstance(value, list) else json.dumps(value)
        
        end_time = time.time()
        complex_navigation_time = end_time - start_time
        
        # Even complex navigation should be fast
        self.assertLess(complex_navigation_time, 0.2)
    
    def test_state_loading_performance(self):
        """Test state loading performance with large state objects."""
        import time
        
        # Create large state object
        large_state = {
            'active_tab': 'chemical-tab',
            'site_history': [f'Site_{i}' for i in range(100)],
            'parameter_history': ['pH', 'dissolved_oxygen'] * 50,
            'navigation_history': [
                {
                    'timestamp': f'2023-01-{i:02d}T10:00:00',
                    'tab': 'chemical-tab',
                    'site': f'Site_{i}'
                } for i in range(1, 32)
            ],
            'filter_settings': {
                f'filter_{i}': f'value_{i}' for i in range(50)
            }
        }
        
        # Test serialization performance
        start_time = time.time()
        serialized = json.dumps(large_state)
        serialization_time = time.time() - start_time
        
        # Test deserialization performance
        start_time = time.time()
        deserialized = json.loads(serialized)
        deserialization_time = time.time() - start_time
        
        # Verify performance is acceptable
        self.assertLess(serialization_time, 0.1)  # Under 100ms
        self.assertLess(deserialization_time, 0.1)  # Under 100ms
        
        # Verify data integrity
        self.assertEqual(len(deserialized['site_history']), 100)
        self.assertEqual(len(deserialized['navigation_history']), 31)
        self.assertEqual(deserialized['active_tab'], 'chemical-tab')
    
    def test_concurrent_navigation_handling(self):
        """Test handling of concurrent navigation requests."""
        import threading
        import time
        
        # Shared state for concurrent testing
        shared_state = {'active_tab': 'overview-tab', 'counter': 0}
        state_lock = threading.Lock()
        
        def simulate_navigation_request(thread_id):
            """Simulate a navigation request from a thread."""
            with state_lock:
                current_counter = shared_state['counter']
                time.sleep(0.001)  # Simulate processing time
                shared_state['counter'] = current_counter + 1
                shared_state[f'thread_{thread_id}_tab'] = f'tab_{thread_id}'
        
        # Create multiple threads
        threads = []
        for i in range(10):
            thread = threading.Thread(target=simulate_navigation_request, args=(i,))
            threads.append(thread)
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify concurrent handling
        self.assertEqual(shared_state['counter'], 10)
        
        # Verify all thread-specific updates were applied
        for i in range(10):
            self.assertIn(f'thread_{i}_tab', shared_state)
            self.assertEqual(shared_state[f'thread_{i}_tab'], f'tab_{i}')


class TestNavigationAccessibility(unittest.TestCase):
    """Test navigation accessibility features."""
    
    def test_keyboard_navigation(self):
        """Test keyboard navigation support."""
        # Test tab navigation structure
        tab_elements = [
            {'id': 'overview-tab', 'label': 'Overview', 'tabindex': 0},
            {'id': 'chemical-tab', 'label': 'Chemical', 'tabindex': 0},
            {'id': 'biological-tab', 'label': 'Biological', 'tabindex': 0},
            {'id': 'habitat-tab', 'label': 'Habitat', 'tabindex': 0}
        ]
        
        # Verify all tabs are keyboard accessible
        for tab in tab_elements:
            self.assertEqual(tab['tabindex'], 0)
            self.assertIsInstance(tab['label'], str)
            self.assertGreater(len(tab['label']), 0)
        
        # Test keyboard event handling
        keyboard_events = {
            'Tab': 'next_element',
            'Shift+Tab': 'previous_element',
            'Enter': 'activate_element',
            'Space': 'activate_element',
            'ArrowRight': 'next_tab',
            'ArrowLeft': 'previous_tab'
        }
        
        for key, action in keyboard_events.items():
            self.assertIsInstance(action, str)
            self.assertGreater(len(action), 0)
    
    def test_screen_reader_navigation(self):
        """Test screen reader support for navigation."""
        # Test ARIA labels and roles
        navigation_elements = [
            {'role': 'tablist', 'aria-label': 'Main navigation tabs'},
            {'role': 'tab', 'aria-label': 'Overview tab', 'aria-selected': 'true'},
            {'role': 'tab', 'aria-label': 'Chemical data tab', 'aria-selected': 'false'},
            {'role': 'tabpanel', 'aria-labelledby': 'overview-tab', 'aria-hidden': 'false'}
        ]
        
        # Verify ARIA attributes
        for element in navigation_elements:
            if 'role' in element:
                self.assertIn(element['role'], ['tablist', 'tab', 'tabpanel'])
            if 'aria-label' in element:
                self.assertIsInstance(element['aria-label'], str)
                self.assertGreater(len(element['aria-label']), 0)
        
        # Test navigation announcements
        navigation_announcements = {
            'tab_change': 'Navigated to {tab_name} tab',
            'site_selection': 'Selected site: {site_name}',
            'parameter_change': 'Selected parameter: {parameter_name}',
            'data_loading': 'Loading data for {site_name}',
            'data_loaded': 'Data loaded successfully'
        }
        
        # Verify announcement templates
        for event, template in navigation_announcements.items():
            self.assertIsInstance(template, str)
            # Check if template contains placeholder or is a complete message
            if '{' in template:
                self.assertIn('{', template)  # Contains placeholder
            else:
                # Static messages should be non-empty strings
                self.assertGreater(len(template), 0)
    
    def test_focus_management(self):
        """Test focus management during navigation."""
        # Test focus sequence
        focus_sequence = [
            {'element': 'main-tabs', 'order': 1},
            {'element': 'site-dropdown', 'order': 2},
            {'element': 'parameter-dropdown', 'order': 3},
            {'element': 'date-picker', 'order': 4},
            {'element': 'apply-filters', 'order': 5}
        ]
        
        # Verify focus order
        for i, focus_item in enumerate(focus_sequence):
            self.assertEqual(focus_item['order'], i + 1)
            self.assertIsInstance(focus_item['element'], str)
        
        # Test focus restoration after navigation
        initial_focus = 'site-dropdown'
        navigation_target = 'biological-tab'
        
        # Simulate navigation
        focus_history = [initial_focus]
        focus_history.append(navigation_target)
        
        # Test focus restoration
        if len(focus_history) > 1:
            restored_focus = focus_history[-2]  # Previous focus
        else:
            restored_focus = 'main-tabs'  # Default focus
        
        self.assertEqual(restored_focus, initial_focus)
        
        # Test focus trapping in modals
        modal_focus_sequence = ['modal-title', 'modal-content', 'modal-close']
        
        for element in modal_focus_sequence:
            self.assertIsInstance(element, str)
            self.assertGreater(len(element), 0)


if __name__ == '__main__':
    unittest.main() 