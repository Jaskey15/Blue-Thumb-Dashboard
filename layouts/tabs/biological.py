"""
Biological tab layout for the Tenmile Creek Water Quality Dashboard.
"""

import dash_bootstrap_components as dbc
from dash import dcc, html
from utils import load_markdown_content

def create_biological_tab():
    """Create the biological data tab layout with searchable dropdown for site selection."""
    return html.Div([
        # Description - always visible
        html.Div([
            html.P([
                load_markdown_content('biological/biological_intro.md')
            ]),
            html.P([
                "Select a community type and search for a site below to begin analysis. "
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
        
        # Site selection section - simplified with searchable dropdown
        html.Div([
            html.Label("Select Site:", className="form-label mb-2", style={'fontWeight': 'bold'}),
            
            # Helper text
            html.Small(
                "Click the dropdown and start typing to search for monitoring sites",
                className="text-muted mb-2 d-block"
            ),

            # Searchable dropdown for site selection
            dcc.Dropdown(
                id='biological-site-dropdown',
                options=[],  # Will be populated when community is selected
                placeholder="Search for a site...",
                searchable=True,
                clearable=True,
                disabled=True,  # Start disabled until community is selected
                className="mb-3"
            )
            
        ], id='biological-site-search-section', style={'display': 'none', 'marginBottom': '20px'}),
        
        # Content container - shows biological data after both selections are made
        html.Div(id='biological-content-container', className="mt-4"),
        
        # Legacy controls content section - keeping for compatibility with existing callbacks
        html.Div(id="biological-controls-content", style={'display': 'none'})
    ]) 