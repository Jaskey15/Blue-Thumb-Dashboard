"""
Overview tab layout for the Tenmile Creek Water Quality Dashboard.
"""

import dash_bootstrap_components as dbc
from dash import dcc, html
from utils import load_markdown_content, create_image_with_caption
from ..constants import PARAMETER_OPTIONS, TAB_STYLES

def create_overview_tab():
    """
    Create the layout for the Overview tab.
    
    Returns:
        HTML layout for the Overview tab
    """
    try:
        # Create the layout WITHOUT creating the map
        tab_content = html.Div([
            # First row: Overview text and image
            dbc.Row([
                # Left column for text 
                dbc.Col([
                    load_markdown_content('overview/overview.md')
                ], width=6),
                
                # Right column for image 
                dbc.Col([
                    html.Div([
                        create_image_with_caption(
                            src='/assets/images/healthy_stream_diagram.png',
                            caption="The key elements of a healthy stream ecosystem include riparian vegetation, diverse aquatic life, and clean water flow."
                        )
                    ], className="d-flex align-items-center justify-content-center h-100 flex-column")
                ], width=6, style={"display": "flex", "align-items": "center"})
            ]),
            
            # Second row: Monitoring Site Locations section
            dbc.Row([
                dbc.Col([
                    html.H3("Monitoring Site Locations", className="mt-4 mb-3"),
                    load_markdown_content('overview/monitoring_sites.md')
                ], width=12)
            ]),
            
            # Third row: Parameter selection dropdown
            dbc.Row([
                dbc.Col([
                    html.Label(
                        "Select parameter to view current status:", 
                        style={"margin-bottom": "5px", "fontWeight": "bold"},
                    ),
                    dcc.Dropdown(
                        id='parameter-dropdown',
                        options=PARAMETER_OPTIONS,
                        value=None,
                        placeholder="Select a parameter...",
                        disabled=True,  # Start disabled
                        clearable=True,
                        style={"width": "100%"}
                    ),
                    html.Small(
                        "Click the × to clear selection and reset map", 
                        className="text-muted mt-1 d-block"
                    )
                ], width=12)
            ], className="mt-3 mb-3"),

            # Fourth row: Active sites toggle - UPDATED TO MATCH CHEMICAL TAB STYLING
            dbc.Row([
                dbc.Col([
                    html.Label(
                        "Active sites only:", 
                        style={
                            "display": "inline-block", 
                            "vertical-align": "middle", 
                            "margin-right": "10px", 
                            "fontWeight": "bold"
                        }
                    ),
                    dbc.Switch(
                        id='active-sites-only-toggle',
                        value=False,  # Default to showing all sites
                        style={"display": "inline-block", "vertical-align": "middle"}
                    )
                ], width=12)
            ], className="mb-3"),
            
            # Fifth row: Map (empty initially, filled by callback)
            dbc.Row([
                dbc.Col([
                    dcc.Graph(
                        id='site-map-graph',
                        figure={},  # Empty figure - callback will populate
                        config={
                            'scrollZoom': True,
                            'displayModeBar': True,
                            'modeBarButtonsToRemove': ['lasso2d', 'select2d']
                        }
                    )
                ], width=12)
            ]),
            
            # Sixth row: Dynamic Legend Container
            dbc.Row([
                dbc.Col([
                    html.Div(id='map-legend-container', className="text-center mt-2 mb-4")
                ], width=12)
            ])
        ], className="tab-content-wrapper")
        
        return tab_content
        
    except Exception as e:
        print(f"Error creating overview tab: {e}")
        return html.Div([
            html.Div("Error loading overview tab content", className="alert alert-danger"),
            html.Pre(str(e), style={"fontSize": "12px"})
        ]) 