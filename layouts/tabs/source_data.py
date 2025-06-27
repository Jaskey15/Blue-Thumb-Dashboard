"""
Source Data tab layout for the Tenmile Creek Water Quality Dashboard.
"""

import dash_bootstrap_components as dbc
from dash import html
from utils import load_markdown_content
from ..constants import TAB_STYLES

def create_source_data_tab():
    """
    Create the layout for the Source Data tab.
    
    Returns:
        HTML layout for the Source Data tab
    """
    try:
        # Create data source cards
        data_source_cards = [
            # Historical Data Card
            dbc.Card([
                dbc.CardHeader([
                    html.Div([
                        # Space reserved for icon (to be added later)
                        html.Div(style={"width": "40px", "height": "40px", "margin-right": "12px", "flex-shrink": "0"}),
                        html.H5("Historical Data (Pre-2020)", className="action-title")
                    ], className="action-header-content")
                ]),
                dbc.CardBody([
                    html.P("Full biological and habitat data as well as chemical data collected before 2020", 
                           className="card-text mb-3"),
                    dbc.Button(
                        [html.I(className="fas fa-external-link-alt me-2"), "Access OCC Data Application"],
                        href="https://occwaterquality.shinyapps.io/OCC-app23b/",
                        target="_blank",
                        color="primary",
                        className="w-100"
                    )
                ])
            ], className="action-card mb-4 shadow-sm"),
            
            # Current Chemical Data Card
            dbc.Card([
                dbc.CardHeader([
                    html.Div([
                        # Space reserved for icon (to be added later)
                        html.Div(style={"width": "40px", "height": "40px", "margin-right": "12px", "flex-shrink": "0"}),
                        html.H5("Current Chemical Data (2020+)", className="action-title")
                    ], className="action-header-content")
                ]),
                dbc.CardBody([
                    html.P("Chemical data collected since January 2020 with interactive mapping capabilities", 
                           className="card-text mb-3"),
                    dbc.Button(
                        [html.I(className="fas fa-external-link-alt me-2"), "Access Blue Thumb App Map"],
                        href="https://okconservation.maps.arcgis.com/apps/webappviewer/index.html?id=1654493dccdd42c29d170785c6b242bf",
                        target="_blank",
                        color="primary",
                        className="w-100"
                    )
                ])
            ], className="action-card mb-4 shadow-sm"),
            
            # Site Interpretations Card
            dbc.Card([
                dbc.CardHeader([
                    html.Div([
                        # Space reserved for icon (to be added later)
                        html.Div(style={"width": "40px", "height": "40px", "margin-right": "12px", "flex-shrink": "0"}),
                        html.H5("Site Interpretations", className="action-title")
                    ], className="action-header-content")
                ]),
                dbc.CardBody([
                    html.P("Volunteer written data interpretations for specific monitoring sites", 
                           className="card-text mb-3"),
                    dbc.Button(
                        [html.I(className="fas fa-external-link-alt me-2"), "Visit Blue Thumb Website"],
                        href="https://www.bluethumbok.com/volunteer-written-data-interpretations.html",
                        target="_blank",
                        color="primary",
                        className="w-100"
                    )
                ])
            ], className="action-card mb-4 shadow-sm")
        ]
        
        tab_content = html.Div([
            # Main title
            dbc.Row([
                dbc.Col([
                    html.H3("Source Data", className="mb-4")
                ], width=12)
            ]),
            
            # Data source cards in responsive grid
            dbc.Row([
                dbc.Col([
                    card
                ], width=12, md=6, lg=4) for card in data_source_cards
            ], className="mb-4")
        ], className="tab-content-wrapper")
        
        return tab_content
        
    except Exception as e:
        print(f"Error creating source data tab: {e}")
        return html.Div([
            html.Div("Error loading source data tab content", className="alert alert-danger"),
            html.Pre(str(e), style={"fontSize": "12px"})
        ]) 