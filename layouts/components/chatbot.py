"""
Floating chatbot component for Blue Thumb dashboard
"""

import dash_bootstrap_components as dbc
from dash import dcc, html


def create_floating_chatbot(tab_name):
    """
    Create a floating chatbot widget that can be added to any tab
    
    Args:
        tab_name (str): Name of the current tab for context-aware responses
        
    Returns:
        dash component: A collapsible chat widget
    """
    return html.Div([
        # Interval to hide callout after a delay
        dcc.Interval(
            id={'type': 'chat-callout-interval', 'tab': tab_name},
            interval=8 * 1000,  # 8 seconds
            n_intervals=0,
            max_intervals=1,
        ),

        # Callout bubble
        html.Div(
            [
                "Have questions? Ask me here!",
                html.Div(className="callout-arrow"),
            ],
            id={'type': 'chat-callout', 'tab': tab_name},
            className="chat-callout",
            style={"display": "block"} # Start visible
        ),

        # Chat toggle button
        dbc.Button(
            [html.I(className="fas fa-comments me-2"), "Ask about Stream Health"],
            id={"type": "chat-toggle", "tab": tab_name},
            color="primary",
            size="lg",
            className="position-fixed",
            style={
                "bottom": "20px",
                "right": "20px",
                "zIndex": "1050",
                "borderRadius": "30px",
                "boxShadow": "0 2px 5px rgba(0,0,0,0.2)"
            }
        ),
        
        # Chat panel
        dbc.Collapse(
            dbc.Card([
                # Header
                dbc.CardHeader([
                    html.H5("Stream Health Assistant", className="m-0"),
                    dbc.Button(
                        html.I(className="fas fa-minus"),
                        id={"type": "chat-close", "tab": tab_name},
                        size="sm",
                    )
                ], className="d-flex justify-content-between align-items-center chat-panel-header"),
                
                # Chat messages container
                dbc.CardBody([
                    html.Div(
                        id={"type": "chat-messages", "tab": tab_name},
                        className="chat-messages-container",
                        style={
                            "height": "300px",
                            "overflowY": "auto",
                            "marginBottom": "10px"
                        }
                    ),
                    
                    # Input area
                    dbc.InputGroup([
                        dbc.Textarea(
                            id={"type": "chat-input", "tab": tab_name},
                            placeholder="Ask a question about stream health...",
                            rows=2,
                            style={"resize": "none"}
                        ),
                        dbc.InputGroupText(
                            dbc.Button(
                                html.I(className="fas fa-paper-plane"),
                                id={"type": "chat-submit", "tab": tab_name},
                                color="primary",
                                size="sm",
                                style={"width": "100%"}
                            ),
                            style={"backgroundColor": "transparent", "border": "none"}
                        )
                    ])
                ]),
                
                # Loading spinner
                dbc.Spinner(
                    html.Div(id={"type": "chat-loading", "tab": tab_name}),
                    type="border",
                    fullscreen=False,
                    color="primary",
                    spinner_style={"width": "1.5rem", "height": "1.5rem"}
                )
            ], className="chat-panel"),
            id={"type": "chat-collapse", "tab": tab_name},
            is_open=False,
            style={
                "position": "fixed",
                "bottom": "80px",
                "right": "20px",
                "width": "350px",
                "zIndex": "1040"
            }
        ),
        dcc.Store(id={'type': 'chat-request-store', 'tab': tab_name}),
        dcc.Store(id={'type': 'chat-scroll-store', 'tab': tab_name})
    ]) 