"""
Overview tab layout for the dashboard
"""

import dash_bootstrap_components as dbc
from dash import dcc, html

from utils import load_markdown_content

from ..components.chatbot import create_floating_chatbot
from ..constants import PARAMETER_OPTIONS


def create_overview_tab():
    """
    Create the layout for the Overview tab.
    
    Returns:
        HTML layout for the Overview tab
    """
    try:
        tab_content = html.Div([
            # Monitoring site locations section
            dbc.Row([
                dbc.Col([
                    load_markdown_content('monitoring_sites.md')
                ], width=12)
            ]),
            
            # Parameter selection
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

            # Active sites toggle
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
            
            # Map visualization
            dbc.Row([
                dbc.Col([
                    dcc.Graph(
                        id='site-map-graph',
                        figure={},  # Empty figure - populated by callback
                        config={
                            'scrollZoom': True,
                            'displayModeBar': True,
                            'modeBarButtonsToRemove': ['lasso2d', 'select2d']
                        }
                    )
                ], width=12)
            ]),
            
            # Dynamic legend container
            dbc.Row([
                dbc.Col([
                    html.Div(id='map-legend-container', className="text-center mt-2 mb-4")
                ], width=12)
            ])
        ], className="tab-content-wrapper")
        
        return html.Div([
            tab_content,
            create_floating_chatbot('overview')
        ])
        
    except Exception as e:
        print(f"Error creating overview tab: {e}")
        return html.Div([
            html.Div("Error loading overview tab content", className="alert alert-danger"),
            html.Pre(str(e), style={"fontSize": "12px"})
        ]) 