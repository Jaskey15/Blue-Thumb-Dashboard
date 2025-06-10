"""
Biological tab layout for the Tenmile Creek Water Quality Dashboard.
"""

import dash_bootstrap_components as dbc
from dash import dcc, html
from utils import load_markdown_content

def create_biological_tab():
    """Create the biological data tab layout with community-first selection."""
    return html.Div([
        # Description - always visible
        html.Div([
            html.P([
                load_markdown_content('biological/biological_intro.md')
            ]),
            html.P([
                "Select a community type and search for a site below to begin analysis."
                "You can find site names and locations on the ",
                html.A("Overview tab.", id="biological-overview-link", href="#", style={"text-decoration": "underline"}),
                
            ])
        ], className="mb-4"),
        
        # Community selection - always visible
        html.Div([
            html.Label("Select Biological Community:", className="form-label mb-2", style={'fontWeight': 'bold'}),
            dcc.Dropdown(
                id='biological-community-dropdown',
                options=[
                    {'label': 'Select a community type...', 'value': '', 'disabled': True},
                    {'label': 'Fish Community', 'value': 'fish'},
                    {'label': 'Macroinvertebrate Community', 'value': 'macro'}
                ],
                value='',  # Start with no selection
                placeholder="Choose a biological community",
                className="mb-3"
            )
        ], className="mb-4"),
        
        # Site search section - hidden until community is selected
        html.Div([
            html.Label("Select Site:", className="form-label mb-2", style={'fontWeight': 'bold'}),
            
            # Helper text
            html.Small(
                "Enter a search term and click 'Search' or press enter to find monitoring sites",
                className="text-muted mb-2 d-block"
            ),

            # Search input with button
            html.Div([
                dbc.InputGroup([
                    dbc.Input(
                        id='biological-search-input',
                        placeholder="Enter site name (e.g., Tenmile, Boggy, Blue)",
                        type="text",
                        value="",
                        disabled=True,  # Start disabled
                        n_submit=0
                    ),
                    dbc.Button(
                        "Search",
                        id='biological-search-button',
                        color="primary",
                        n_clicks=0,
                        disabled=True  # Start disabled
                    ),
                    dbc.Button(
                        "Clear",
                        id='biological-clear-button',
                        color="secondary",
                        n_clicks=0,
                        disabled=True  # Start disabled
                    )
                ])
            ], style={'position': 'relative', 'marginBottom': '5px'}),
            
            # Search results list (initially hidden)
            html.Div(
                id='biological-search-results',
                children=[],
            ),
            
            # Hidden store for selected site
            dcc.Store(id='biological-selected-site', data=None)
            
        ], id='biological-site-search-section', style={'display': 'none', 'position': 'relative', 'marginBottom': '20px'}),
        
        # Content container - shows biological data after both selections are made
        html.Div(id='biological-content-container', className="mt-4"),
        
        # Legacy controls content section - keeping for compatibility with existing callbacks
        html.Div(id="biological-controls-content", style={'display': 'none'})
    ]) 