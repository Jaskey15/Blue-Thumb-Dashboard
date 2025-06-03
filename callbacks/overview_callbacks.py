"""
Overview callbacks for the Tenmile Creek Water Quality Dashboard.
This file contains callbacks specific to the overview tab.
"""

import dash
import plotly.graph_objects as go
from callbacks.helper_functions import get_parameter_name
from dash import html, Input, Output, State  
from .helper_functions import get_parameter_legend, get_site_count_message, get_parameter_label
from visualizations.map_viz import add_site_marker
from utils import setup_logging

# Configure logging
logger = setup_logging("overview_callbacks", category="callbacks")

def register_overview_callbacks(app):
    """Register all callbacks for the overview tab."""
    
    @app.callback(
        [Output('site-map-graph', 'figure'),
        Output('parameter-dropdown', 'disabled'),
        Output('map-legend-container', 'children')],
        [Input('main-tabs', 'active_tab')]
    )
    def load_basic_map_on_tab_open(active_tab):
        """
        Load the basic map when the Overview tab is opened.
        This shows different shapes and colors for active vs historic sites.
        """
        # Only load map when Overview tab is active
        if active_tab != 'overview-tab':
            return dash.no_update, dash.no_update, dash.no_update
        
        try:
            from visualizations.map_viz import create_basic_site_map
            
            # Create basic map with site counts
            basic_map, active_count, historic_count, total_count = create_basic_site_map()
            
            # Enable the parameter dropdown now that map is loaded
            dropdown_disabled = False
            
            # Create legend for basic map
            legend_content = [
                # Site count display
                html.Div(
                    f"Showing {total_count} monitoring sites",
                    className="text-center mb-2",
                    style={"font-weight": "bold", "color": "#666"}
                ),
                # Legend items
                html.Div([
                    html.Div([
                        html.Span("●", style={"color": "#3366CC", "font-size": "16px"}),  # Larger circle for active
                        html.Span(" Active Sites", className="mr-3")
                    ], style={"display": "inline-block", "margin-right": "15px"}),
                    html.Div([
                        html.Span("●", style={"color": "#9370DB", "font-size": "12px"}),  # Smaller circle for historic
                        html.Span(" Historic Sites", className="mr-3")
                    ], style={"display": "inline-block", "margin-right": "15px"})
                ])
            ]

            legend_html = html.Div(legend_content, className="text-center mt-2 mb-4")
            
            return basic_map, dropdown_disabled, legend_html
            
        except Exception as e:
            logger.error(f"Error loading basic map: {e}")
            
            # Return empty map and keep dropdown disabled
            empty_map = {
                'data': [],
                'layout': {
                    'title': 'Error loading map',
                    'xaxis': {'visible': False},
                    'yaxis': {'visible': False}
                }
            }
            
            return empty_map, True, html.Div()
        
    @app.callback(
        [Output('site-map-graph', 'figure', allow_duplicate=True),
        Output('map-legend-container', 'children', allow_duplicate=True)],
        [Input('parameter-dropdown', 'value'),
        Input('active-sites-only-toggle', 'value')],  # Add the toggle as input
        [State('site-map-graph', 'figure')],
        prevent_initial_call=True
    )
    def update_map_with_parameter_selection(parameter_value, active_only_toggle, current_figure):
        """
        Update the map with parameter-specific color coding when user selects a parameter
        or toggles the active sites filter.
        """
        try:
            from visualizations.map_viz import create_basic_site_map, add_parameter_colors_to_map, filter_sites_by_active_status, MONITORING_SITES
            
            # Filter sites based on toggle state
            filtered_sites, active_count, historic_count, total_original = filter_sites_by_active_status(
                MONITORING_SITES, active_only_toggle
            )
            
            # If no parameter selected, show basic map with filtered sites
            if not parameter_value:
                # Create basic map with filtered sites
                fig = go.Figure()  # Start with empty figure
                sites_with_data = 0
                total_sites = len(filtered_sites)
                
                # Add all filtered sites with basic styling
                for site in filtered_sites:
                    hover_text = (f"Site: {site['name']}<br>"
                                f"County: {site['county']}<br>"
                                f"River Basin: {site['river_basin']}<br>"
                                f"Ecoregion: {site['ecoregion']}")
                    
                    fig = add_site_marker(
                        fig=fig,
                        lat=site["lat"],
                        lon=site["lon"],
                        color='',
                        site_name=site["name"],
                        hover_text=hover_text,
                        active=site["active"]
                    )
                
                # Set up basic map layout
                fig.update_layout(
                    map=dict(
                        style="white-bg",
                        layers=[{
                            "below": 'traces',
                            "sourcetype": "raster",
                            "sourceattribution": "Esri",
                            "source": [
                                "https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}"
                            ]
                        }],
                        center=dict(lat=35.5, lon=-98.2),
                        zoom=6.2
                    ),
                    margin=dict(l=0, r=0, t=0, b=0),
                    height=600,
                    showlegend=False,
                    title=dict(text="Monitoring Sites", x=0.5, y=0.98)
                )
                
                # Create legend for basic map
                if active_only_toggle:
                    count_text = f"Showing {len(filtered_sites)} of {total_original} monitoring sites (active only)"
                else:
                    count_text = f"Showing {total_original} monitoring sites ({active_count} active, {historic_count} historic)"
                
                legend_content = [
                    html.Div(count_text, className="text-center mb-2", style={"font-weight": "bold", "color": "#666"}),
                    html.Div([
                        html.Div([
                            html.Span("● ", style={"color": "#3366CC", "font-size": "20px"}),
                            html.Span("Active Sites", className="mr-3")
                        ], style={"display": "inline-block", "margin-right": "15px"}),
                        html.Div([
                            html.Span("▲ ", style={"color": "#9370DB", "font-size": "20px"}),
                            html.Span("Historic Sites", className="mr-3")
                        ], style={"display": "inline-block", "margin-right": "15px"}) if not active_only_toggle else html.Div()
                    ])
                ]
                
                legend_html = html.Div(legend_content, className="text-center mt-2 mb-4")
                return fig, legend_html
            
            # If parameter is selected, add parameter-specific colors
            param_type, param_name = parameter_value.split(':')
            
            # Start with current figure or create basic map
            if current_figure and current_figure.get('data'):
                fig = go.Figure(current_figure)
            else:
                fig = go.Figure()
            
            # Add parameter-specific colors with filtered sites
            updated_map, sites_with_data, total_sites = add_parameter_colors_to_map(fig, param_type, param_name, filtered_sites)
            
            # Create appropriate legend based on parameter type and name
            legend_items = get_parameter_legend(param_type, param_name)
            legend_items = [item for item in legend_items if "No data" not in item["label"]]
            
            # Build the legend HTML with updated site count
            if active_only_toggle:
                count_text = f"Showing {sites_with_data} of {total_original} monitoring sites (active only) with {get_parameter_name(param_name)} data"
            else:
                count_text = get_site_count_message(param_type, param_name, sites_with_data, total_sites)
            
            legend_content = [
                html.Div(count_text, className="text-center mb-2", style={"font-weight": "bold", "color": "#666"}),
                html.Div([
                    html.Div([
                        html.Span("● ", style={"color": item["color"], "font-size": "20px"}),
                        html.Span(item["label"], className="mr-3")
                    ], style={"display": "inline-block", "margin-right": "15px"})
                    for item in legend_items
                ])
            ]

            legend_html = html.Div(legend_content, className="text-center mt-2 mb-4")
            return updated_map, legend_html
            
        except Exception as e:
            logger.error(f"Error updating map with parameter selection: {e}")
            return dash.no_update, html.Div(
                html.Div("Error updating map. Please try again.", className="text-danger"),
                className="text-center mt-2 mb-4"
            )