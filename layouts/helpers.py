"""
Helper functions for the Dashboard
"""

import dash_bootstrap_components as dbc
from dash import dcc, html
from utils import create_image_with_caption

def create_species_gallery(species_type):
    """
    Create a gallery layout for either fish or macroinvertebrates.
    
    Args:
        species_type: Type of species gallery ('fish' or 'macro')
        
    Returns:
        HTML layout for the species gallery
    """
    # Determine gallery title based on species type
    title = (
        "Common Fish Found in Oklahoma Streams" 
        if species_type == 'fish' 
        else "Common Macroinvertebrates Found in Oklahoma Streams"
    )
    
    # Create ID strings for components
    container_id = f"{species_type}-gallery-container"
    prev_button_id = f"prev-{species_type}-button"
    next_button_id = f"next-{species_type}-button"
    index_store_id = f"current-{species_type}-index"
    
    return html.Div([
        # Gallery title
        html.H5(title, className="text-center mt-4"),
        
        # Container for the gallery with fixed height
        html.Div(
            id=container_id,
            className="text-center",
            style={'min-height': '400px'}  
        ),
        
        # Navigation buttons
        dbc.Row([
            dbc.Col(
                dbc.Button("Previous", id=prev_button_id, color="primary", className="mr-2"),
                width={"size": 2, "offset": 4},
            ),
            dbc.Col(
                dbc.Button("Next", id=next_button_id, color="primary"),
                width=2,
            ),
        ], className="mt-3"),
        
        # Hidden store for current index
        dcc.Store(id=index_store_id, data=0),
    ])

def create_action_card(icon, title, why_text, tips_list, category=None):
    """
    Create a single action card for stream protection actions.
    
    Args:
        icon: Icon filename (without extension) for the card
        title: Card title text
        why_text: Text explaining why the action matters
        tips_list: List of tips for implementing the action
        category: Optional category for styling/filtering
        
    Returns:
        A Card component for the action
    """
    return dbc.Card([
        # Card header with icon and title
        dbc.CardHeader([
            html.Div([
                html.Img(src=f"/assets/icons/{icon}.png", className="action-icon"),
                html.H5(title, className="action-title"),
            ], className="action-header-content"),
        ]),
        # Card body with explanatory text and tips
        dbc.CardBody([
            html.Div([
                html.H6("WHY IT MATTERS", className="text-muted mb-2"),
                html.P(why_text, className="mb-3"),
                html.H6("HOW TO DO IT", className="text-muted mb-2"),
                html.Ul([html.Li(tip) for tip in tips_list], className="mb-0")
            ])
        ])
    ], className=f"action-card mb-4 h-100 {category if category else ''}")

def create_dropdown_row(id_value, label_text, options, default_value=None, clearable=False, placeholder=None):
    """
    Create a consistent row layout with a dropdown.
    
    Args:
        id_value: ID for the dropdown component
        label_text: Text for the dropdown label
        options: List of dropdown options
        default_value: Initial value for the dropdown
        clearable: Whether the dropdown is clearable
        placeholder: Placeholder text when no value is selected
        
    Returns:
        A Row component containing the dropdown
    """
    return dbc.Row([
        dbc.Col([
            html.Label(
                label_text, 
                style={"margin-bottom": "5px"}
            ),
            dcc.Dropdown(
                id=id_value,
                options=options,
                value=default_value,
                clearable=clearable,
                placeholder=placeholder or "Select an option...",
                style={"width": "100%"}
            )
        ], width=12)
    ], className="mb-2")

def create_season_month_selectors():
    """
    Create the season and month selection controls for chemical data filtering.
    
    Returns:
        A Row component with season buttons and month checklist
    """
    return dbc.Row([
        # Season Selection (left side)
        dbc.Col([
            html.Label(
                "Select Season:", 
                style={"display": "inline-block", "vertical-align": "middle", "margin-right": "10px"}
            ),
            dbc.ButtonGroup(
                [
                    dbc.Button("ALL", color="secondary", id="select-all-months", n_clicks=1, active=True),
                    dbc.Button("SPRING", color="success", id="select-spring", n_clicks=0),
                    dbc.Button("SUMMER", color="warning", id="select-summer", n_clicks=0),
                    dbc.Button("FALL", color="danger", id="select-fall", n_clicks=0),
                    dbc.Button("WINTER", color="info", id="select-winter", n_clicks=0)
                ],
                style={"display": "inline-block", "vertical-align": "middle"}
            )
        ], width=5),

        # Month selection (right side)
        dbc.Col([
            html.Label(
                "Select Months:", 
                style={"display": "inline-block", "vertical-align": "middle", "margin-right": "10px"}
            ),
            dcc.Checklist(
                id='month-checklist',
                options=[
                    {'label': 'Jan', 'value': 1}, {'label': 'Feb', 'value': 2},
                    {'label': 'Mar', 'value': 3}, {'label': 'Apr', 'value': 4},
                    {'label': 'May', 'value': 5}, {'label': 'Jun', 'value': 6},
                    {'label': 'Jul', 'value': 7}, {'label': 'Aug', 'value': 8},
                    {'label': 'Sep', 'value': 9}, {'label': 'Oct', 'value': 10},
                    {'label': 'Nov', 'value': 11}, {'label': 'Dec', 'value': 12}
                ],
                value=list(range(1, 13)),  # Default to all months
                inline=True,
                style={"display": "inline-block", "vertical-align": "middle"}
            )
        ], width=7)
    ], className="mb-3") 