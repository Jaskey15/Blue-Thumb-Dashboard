"""
Habitat tab layout for the Dashboard
"""

import dash_bootstrap_components as dbc
from dash import dcc, html
from utils import load_markdown_content

def create_habitat_tab():
    """Create the habitat assessment tab with site search functionality."""
    return html.Div([
        # Description section with two-column layout
        dbc.Row([
            # Left column - intro text AND the additional paragraph
            dbc.Col([
                load_markdown_content('habitat/habitat_intro.md'),
                html.P([
                    "Select a site below to begin analysis. "
                    "You can find site names and locations on the ",
                    html.A("Overview tab.", id="habitat-overview-link", href="#", style={"text-decoration": "underline"}),
                ], className="mt-3")  # Add some top margin to separate from markdown content
            ], width=6),
            
            # Right column - image
            dbc.Col([
                html.Img(
                    src="/assets/images/stream_habitat_diagram.jpg",
                    className="img-fluid",
                    style={'width': '100%', 'height': 'auto'},
                    alt="Stream habitat diagram showing riffle, run, and pool features"
                )
            ], width=6)
        ], className="mb-4"),
        
        # Site search section 
        dbc.Row([
            dbc.Col([
                html.Label("Select Site:", className="form-label mb-2", style={'fontWeight': 'bold'}),
                
                # Helper text
                html.Small(
                    "Enter a search term and click 'Search' or press enter to find monitoring sites",
                    className="text-muted mb-2 d-block"
                ),

                # Search input and button
                html.Div([
                    dbc.InputGroup([
                        dbc.Input(
                            id="habitat-search-input",
                            placeholder="Enter site name (e.g., Tenmile, Boggy, Blue)",
                            type="text",
                            value="",
                            n_submit=0
                        ),
                        dbc.Button(
                            "Search",
                            id="habitat-search-button",
                            color="primary",
                            n_clicks=0
                        ),
                        dbc.Button(
                            "Clear",
                            id="habitat-clear-button",
                            color="secondary",
                            n_clicks=0
                        )
                    ]),
                    
                    # Search results list (initially hidden) 
                    html.Div(
                        id="habitat-search-results",
                        children=[],
                    )
                ], style={'position': 'relative', 'marginBottom': '5px'}), 
            ], width=12)
        ], className="mb-4"),
        
        # Content container (shows visualization when site is selected)
        html.Div(id="habitat-content-container", children=[
            html.P("Select a site above to view habitat assessment data.", 
                   className="text-center text-muted mt-5")
        ]),
        
        # Hidden store for selected site
        dcc.Store(id="habitat-selected-site", data=None)
    ]) 