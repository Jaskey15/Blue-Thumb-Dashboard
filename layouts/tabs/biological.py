"""
Biological tab layout for the Tenmile Creek Water Quality Dashboard.
"""

import dash_bootstrap_components as dbc
from dash import dcc, html
from utils import load_markdown_content

def create_biological_tab():
    """Create the biological data tab layout with searchable dropdown for site selection."""
    return html.Div([
        # Download component (hidden, triggered by callback)
        dcc.Download(id="biological-download-component"),

        # Description - always visible
        html.Div([
            html.H3("Biological Assessment", className="mb-3"),
            html.P([
                "Biological monitoring uses the organisms living in streams as direct indicators of ecosystem health. "
                "Fish and macroinvertebrates serve as nature's report card, reflecting both chemical and physical "
                "conditions over extended periods. This provides a more comprehensive view of stream health than "
                "chemical testing alone, as biological communities integrate all environmental factors throughout "
                "their lifecycle. Select a community type and site below to begin analysis. You can find site "
                "names and location on the ",
                html.A("overview tab", id="biological-overview-link", href="#", style={"text-decoration": "underline"}),
                "."
            ]),
        ], className="mb-4"),
        
        # Community selection - always visible
        html.Div([
            html.Label("Select Biological Community:", className="form-label mb-2", style={'fontWeight': 'bold', 'fontSize': '1rem'}),
            dcc.Dropdown(
                id='biological-community-dropdown',
                options=[
                    {'label': 'Fish Community', 'value': 'fish'},
                    {'label': 'Macroinvertebrate Community', 'value': 'macro'}
                ],
                value='',  # Start with no selection
                placeholder="Select a community type...",
                className="mb-3"
            )
        ], className="mb-2"),
        
        # Site selection section - simplified with searchable dropdown
        html.Div([
            html.Label("Select Site:", className="form-label", style={'fontWeight': 'bold', 'fontSize': '1rem', 'marginBottom': '0.1rem'}),
            
            # Helper text
            html.Small(
                "Click the dropdown and start typing to search for monitoring sites",
                className="text-muted mb-1 d-block"
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
            
        ], id='biological-site-search-section', className="mb-4", style={'display': 'none'}),
        
        # Content container - split into community-specific and site-specific sections
        html.Div([
            # Site-specific content (charts, metrics) - appears first
            html.Div([
                # Download button container
                dbc.Row([
                    dbc.Col([
                        dbc.Button(
                            id="biological-download-btn",
                            color="success",
                            size="sm",
                            style={'display': 'none'}  # Initially hidden
                        )
                    ], width=12, className="d-flex justify-content-end")
                ]),
                
                # Site content container
                html.Div(id='biological-site-content-inner')
            ], id='biological-site-content'),
            
            # Community-specific content (description, gallery, interpretation) - appears second
            html.Div(id='biological-community-content', className="mt-4")
        ], id='biological-content-container', className="mt-4"),
        
        # Legacy controls content section - keeping for compatibility with existing callbacks
        html.Div(id="biological-controls-content", style={'display': 'none'})
    ], className="tab-content-wrapper") 