"""
Habitat tab layout for the Dashboard
"""

import dash_bootstrap_components as dbc
from dash import dcc, html
from utils import load_markdown_content, create_image_with_caption
from layouts.ui_data import HABITAT_DIAGRAMS, HABITAT_DIAGRAM_CAPTIONS

def create_habitat_tab():
    """Create the habitat assessment tab with searchable dropdown for site selection."""
    return html.Div([
        # Download component (hidden, triggered by callback)
        dcc.Download(id="habitat-download-component"),
        
        # Description - always visible (matching chemical tab structure)
        html.Div([
            html.H3("Habitat Assessment", className="mb-3"),
            html.P([
                "Habitat assessment evaluates the physical features of streams that support aquatic life. "
                "As part of Blue Thumb's comprehensive approach to stream health monitoring, habitat data "
                "provides crucial context for interpreting chemical and biological results. Physical habitat "
                "quality directly influences the biotic community and serves as the foundation for a healthy "
                "stream ecosystem. Select a site below to begin analysis. You can find site names and locations on the ",
                html.A("Overview tab", id="habitat-overview-link", href="#", style={"text-decoration": "underline"}),
                "."
            ])
        ], className="mb-4"),
        
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
                id="habitat-site-dropdown",
                options=[],  # Will be populated when tab loads
                placeholder="Search for a site...",
                searchable=True,
                clearable=True,
                className="mb-3"
            )
        ], style={'marginBottom': '20px'}),
        
        # Content container - hidden until site is selected 
        html.Div([
            # Visualizations section
            dbc.Row([
                dbc.Col([
                    html.Div(id="habitat-content-container", children=[
                        html.P("Select a site above to view habitat assessment data.", 
                               className="text-center text-muted mt-5")
                    ])
                ], width=12)
            ], className="mb-4"),
            
            # Description and diagram section 
            dbc.Row([
                dbc.Col([
                    html.Div(id='habitat-explanation-container', children=[
                        load_markdown_content('habitat_analysis.md', link_target="_blank")
                    ])
                ], width=6, className="d-flex"),  
                dbc.Col([
                    html.Div(id='habitat-diagram-container', children=[
                        create_image_with_caption(
                            src=HABITAT_DIAGRAMS['habitat_assessment'],
                            caption=HABITAT_DIAGRAM_CAPTIONS['habitat_assessment'],
                            className="img-fluid tab-image-container",
                            style={'width': '100%', 'height': 'auto'},
                            alt_text="Stream habitat diagram showing riffle, run, and pool features"
                        )
                    ])
                ], width=6, className="d-flex align-items-center")  
            ], className="h-100 align-items-stretch", style={'minHeight': '400px'})
        ], id="habitat-controls-content", style={'display': 'none'}),
        
    ], className="tab-content-wrapper") 