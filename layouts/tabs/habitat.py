"""
Habitat tab layout for the dashboard
"""

import dash_bootstrap_components as dbc
from dash import dcc, html

from layouts.ui_data import HABITAT_DIAGRAM_CAPTIONS, HABITAT_DIAGRAMS
from utils import create_image_with_caption, load_markdown_content

from ..components.chatbot import create_floating_chatbot


def create_habitat_tab():
    """Create the habitat assessment tab with searchable dropdown for site selection."""
    tab_content = html.Div([
        dcc.Download(id="habitat-download-component"),
        
        # Description section
        html.Div([
            html.H3("Habitat Assessment", className="mb-3"),
            html.P([
                "Habitat assessment evaluates the physical features of streams that support aquatic life. "
                "As part of Blue Thumb's comprehensive approach to stream health monitoring, habitat data "
                "provides crucial context for interpreting chemical and biological results. Physical habitat "
                "quality directly influences the biotic community and serves as the foundation for a healthy "
                "stream ecosystem. Select a site below to begin analysis. You can find site names and locations on the ",
                html.A("overview tab", id="habitat-overview-link", href="#", style={"text-decoration": "underline"}),
                "."
            ])
        ], className="mb-4"),
        
        # Site selection
        html.Div([
            html.Label("Select Site:", className="form-label", style={'fontWeight': 'bold', 'fontSize': '1rem', 'marginBottom': '0.1rem'}),
            
            html.Small(
                "Click the dropdown and start typing to search for monitoring sites",
                className="text-muted mb-1 d-block"
            ),

            dcc.Dropdown(
                id="habitat-site-dropdown",
                options=[],  # Populated when tab loads
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
                    html.Div([
                        dbc.Button(
                            [html.I(className="fas fa-download me-2"), "Download Habitat Data"],
                            id="habitat-download-btn",
                            color="success",
                            size="sm",
                        )
                    ], style={'textAlign': 'right'}),
                    
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
            ], className="h-100 align-items-stretch mobile-stack", style={'minHeight': '400px'})
        ], id="habitat-controls-content", style={'display': 'none'}),
        
    ], className="tab-content-wrapper")

    return html.Div([
        tab_content,
        create_floating_chatbot('habitat')
    ]) 