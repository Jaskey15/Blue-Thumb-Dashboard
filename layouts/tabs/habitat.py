"""
Habitat tab layout for the Dashboard
"""

import dash_bootstrap_components as dbc
from dash import dcc, html
from utils import load_markdown_content

def create_habitat_tab():
    """Create the habitat assessment tab with searchable dropdown for site selection."""
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
        
        # Site selection section - simplified with searchable dropdown
        dbc.Row([
            dbc.Col([
                html.Label("Select Site:", className="form-label mb-2", style={'fontWeight': 'bold'}),
                
                # Helper text
                html.Small(
                    "Click the dropdown and start typing to search for monitoring sites",
                    className="text-muted mb-2 d-block"
                ),

                # Searchable dropdown for site selection
                dcc.Dropdown(
                    id="habitat-site-dropdown",
                    options=[],  # Will be populated when tab loads
                    placeholder="Search for a site...",
                    searchable=True,
                    clearable=True,
                    className="mb-3"
                )
            ], width=12)
        ], className="mb-4"),
        
        # Content container (shows visualization when site is selected)
        html.Div(id="habitat-content-container", children=[
            html.P("Select a site above to view habitat assessment data.", 
                   className="text-center text-muted mt-5")
        ]),
    ], className="tab-content-wrapper") 