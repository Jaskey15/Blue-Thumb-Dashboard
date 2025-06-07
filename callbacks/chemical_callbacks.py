"""
Chemical callbacks for the Tenmile Creek Water Quality Dashboard.
This file contains callbacks specific to the chemical data tab.
"""

import dash
from dash import html, Input, Output, State, ALL
from utils import setup_logging
from config.data_definitions import SEASON_MONTHS
from data_processing.chemical_processing import process_chemical_data
from .helper_functions import (
    create_all_parameters_view, create_single_parameter_view,
    should_perform_search, is_item_clicked, extract_selected_item
)

# Configure logging
logger = setup_logging("chemical_callbacks", category="callbacks")

def register_chemical_callbacks(app):
    """Register all chemical-related callbacks in logical workflow order."""
    
    # ===========================
    # 1. SITE SEARCH & SELECTION
    # ===========================
    
    @app.callback(
        [Output('chemical-search-results', 'children'),
         Output('chemical-search-results', 'style')],
        [Input('chemical-search-button', 'n_clicks'),
         Input('chemical-search-input', 'n_submit')],
        [State('chemical-search-input', 'value')],
        prevent_initial_call=True
    )
    def update_chemical_search_results(button_clicks, enter_presses, search_value):
        """Filter and display sites based on search input."""
        if not should_perform_search(button_clicks, enter_presses, search_value, True):
            return [], {'display': 'none'}
        
        try:
            # Get all sites with chemical data
            from data_processing.chemical_processing import get_sites_with_chemical_data
            all_sites = get_sites_with_chemical_data()
            
            if not all_sites:
                return [html.Div("No chemical data available.", 
                            className="p-2 text-warning")], {'display': 'block'}
            
            # Filter sites based on search term (case-insensitive)
            search_term_lower = search_value.lower()
            matching_sites = [
                site for site in all_sites 
                if search_term_lower in site.lower()
            ]
            
            if not matching_sites:
                return [html.Div("No sites match your search.", 
                            className="p-2 text-muted")], {'display': 'block'}
            
            # Create clickable list items with habitat-style formatting
            result_items = []
            for site in matching_sites[:10]:  # Limit to 10 results
                result_items.append(
                    html.Div(
                        site,
                        id={'type': 'chemical-site-option', 'site': site},
                        style={
                            'padding': '8px 12px',
                            'cursor': 'pointer',
                            'borderBottom': '1px solid #eee'
                        },
                        className="site-option",
                        n_clicks=0
                    )
                )
            
            logger.info(f"Chemical search for '{search_value}' found {len(matching_sites)} sites")
            return result_items, {
                'display': 'block',
                'position': 'absolute',
                'top': '100%',
                'left': '0',
                'right': '0',
                'backgroundColor': 'white',
                'border': '1px solid #ccc',
                'borderTop': 'none',
                'maxHeight': '200px',
                'overflowY': 'auto',
                'zIndex': '1000',
                'boxShadow': '0 2px 4px rgba(0,0,0,0.1)'
            }
            
        except Exception as e:
            logger.error(f"Error in chemical search: {e}")
            return [html.Div("Error performing search.", 
                        className="p-2 text-danger")], {'display': 'block'}
    
    @app.callback(
        [Output('chemical-selected-site', 'data'),
         Output('chemical-search-input', 'value'),
         Output('chemical-search-results', 'style', allow_duplicate=True),
         Output('chemical-controls-content', 'style')],
        [Input({'type': 'chemical-site-option', 'site': ALL}, 'n_clicks')],
        [State('chemical-selected-site', 'data')],
        prevent_initial_call=True
    )
    def select_chemical_site(site_clicks, current_site):
        """Handle site selection from search results."""
        if not is_item_clicked(site_clicks):
            return current_site, dash.no_update, dash.no_update, dash.no_update
        
        try:
            selected_site = extract_selected_item('site')
            
            logger.info(f"Chemical site selected: {selected_site}")
            
            return (
                selected_site,  # Store selected site
                selected_site,  # Update search input to show selected site
                {'display': 'none'},  # Hide search results
                {'display': 'block'}  # Show parameter controls
            )
            
        except Exception as e:
            logger.error(f"Error in chemical site selection: {e}")
            return current_site, dash.no_update, dash.no_update, dash.no_update
    
    @app.callback(
        [Output('chemical-search-input', 'value', allow_duplicate=True),
         Output('chemical-selected-site', 'data', allow_duplicate=True),
         Output('chemical-search-results', 'style', allow_duplicate=True),
         Output('chemical-controls-content', 'style', allow_duplicate=True)],
        [Input('chemical-clear-button', 'n_clicks')],
        prevent_initial_call=True
    )
    def clear_chemical_search(n_clicks):
        """Clear search input and reset all selections."""
        if n_clicks:
            logger.info("Chemical search cleared")
            return (
                "",  # Clear search input
                None,  # Clear selected site
                {'display': 'none'},  # Hide search results
                {'display': 'none'}  # Hide parameter controls
            )
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update
    
    # ===========================
    # 2. DATA VISUALIZATION
    # ===========================
    
    @app.callback(
        [Output('chemical-graph-container', 'children'),
         Output('chemical-explanation-container', 'children'),
         Output('chemical-diagram-container', 'children')],
        [Input('chemical-parameter-dropdown', 'value'),
         Input('year-range-slider', 'value'),
         Input('month-checklist', 'value'),
         Input('highlight-thresholds-switch', 'value'),
         Input('chemical-selected-site', 'data')]
    )
    def update_chemical_display(selected_parameter, year_range, selected_months, 
                              highlight_thresholds, selected_site):
        """Update chemical parameter visualization based on user selections."""
        
        # Validate inputs
        if not selected_site:
            return _create_empty_state("Please search for and select a site to view data.")
        
        if not selected_parameter:
            return _create_empty_state("Please select a parameter to visualize.")
        
        try:
            # Log the visualization request
            logger.info(f"Creating chemical visualization for {selected_site}, parameter: {selected_parameter}")
            
            # Create the visualization based on parameter type
            if selected_parameter == 'all':
                return _create_all_parameters_visualization(
                    selected_site, year_range, selected_months, highlight_thresholds
                )
            else:
                return _create_single_parameter_visualization(
                    selected_site, selected_parameter, year_range, 
                    selected_months, highlight_thresholds
                )
                
        except Exception as e:
            logger.error(f"Error creating chemical visualization: {e}")
            return _create_error_state(
                "Error Loading Chemical Data",
                f"Could not load chemical data for {selected_site}. Please try again.",
                str(e)
            )

# ===========================
# HELPER FUNCTIONS
# ===========================

def _create_empty_state(message):
    """Create a consistent empty state display."""
    return (
        html.Div(
            html.P(message, className="text-center text-muted mt-5"),
            style={'minHeight': '300px', 'display': 'flex', 'alignItems': 'center'}
        ),
        html.Div(),  # Empty explanation
        html.Div()   # Empty diagram
    )

def _create_error_state(title, message, error_details):
    """Create a consistent error state display."""
    return (
        html.Div([
            html.H4(title, className="text-danger"),
            html.P(message),
            html.Details([
                html.Summary("Error Details"),
                html.Pre(error_details, style={"fontSize": "12px", "color": "red"})
            ])
        ]),
        html.Div(),  # Empty explanation
        html.Div()   # Empty diagram
    )

def _create_all_parameters_visualization(site, year_range, months, highlight_thresholds):
    """Create visualization for all parameters."""
    try:
        # Get processed data using existing function
        df_filtered, key_parameters, reference_values = process_chemical_data(
            site_name=site, use_db=True
        )
        
        # Filter by year range and months (similar to your existing callback logic)
        if not df_filtered.empty:
            # Filter by year range
            df_filtered = df_filtered[
                (df_filtered['Year'] >= year_range[0]) & 
                (df_filtered['Year'] <= year_range[1])
            ]
            
            # Filter by selected months
            if months:
                df_filtered = df_filtered[df_filtered['Month'].isin(months)]
        
        # Use existing helper function with correct parameters
        graph = create_all_parameters_view(
            df_filtered=df_filtered,
            key_parameters=key_parameters,
            reference_values=reference_values,
            highlight_thresholds=highlight_thresholds
        )
        
        explanation = html.Div([
            html.H4("All Chemical Parameters"),
            html.P("This view shows all chemical parameters measured at this site over time. "
                  "Each parameter is normalized to allow comparison across different measurement scales.")
        ])
        
        return graph, explanation, html.Div()  # No diagram for all parameters
        
    except Exception as e:
        logger.error(f"Error creating all parameters view: {e}")
        raise

def _create_single_parameter_visualization(site, parameter, year_range, months, highlight_thresholds):
    """Create visualization for a single parameter."""
    try:
        # Get processed data using existing function
        df_filtered, key_parameters, reference_values = process_chemical_data(
            site_name=site, use_db=True
        )
        
        # Filter by year range and months (similar to your existing callback logic)
        if not df_filtered.empty:
            # Filter by year range
            df_filtered = df_filtered[
                (df_filtered['Year'] >= year_range[0]) & 
                (df_filtered['Year'] <= year_range[1])
            ]
            
            # Filter by selected months
            if months:
                df_filtered = df_filtered[df_filtered['Month'].isin(months)]
        
        # Use existing helper function with correct parameters
        graph, explanation, diagram = create_single_parameter_view(
            df_filtered=df_filtered,
            parameter=parameter,
            reference_values=reference_values,
            highlight_thresholds=highlight_thresholds
        )
        
        return graph, explanation, diagram
        
    except Exception as e:
        logger.error(f"Error creating single parameter view for {parameter}: {e}")
        raise