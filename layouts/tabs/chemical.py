"""
Chemical tab layout for the Tenmile Creek Water Quality Dashboard.
"""

import dash_bootstrap_components as dbc
from dash import dcc, html
from data_processing.data_queries import get_chemical_date_range
from utils import load_markdown_content


def create_chemical_tab():
    """Create the chemical data tab layout with searchable dropdown for site selection."""

    # Get dynamic date range
    min_year, max_year = get_chemical_date_range()
    
    return html.Div([
        # Description - always visible
        html.Div([
            html.P([
                load_markdown_content('chemical/chemical_intro.md')
            ]),
            html.P([
                "Search for a site below to begin analysis. "
                "You can find site names and locations on the ",
                html.A("Overview tab.", id="chemical-overview-link", href="#", style={"text-decoration": "underline"}),
                
            ])
        ], className="mb-4"),
        
        # Site selection section - simplified with searchable dropdown
        html.Div([
            html.Label("Select Site:", className="form-label mb-2", style={'fontWeight': 'bold', 'fontSize': '1rem'}),
            
            # Helper text
            html.Small(
                "Click the dropdown and start typing to search for monitoring sites",
                className="text-muted mb-2 d-block"
            ),

            # Searchable dropdown for site selection
            dcc.Dropdown(
                id='chemical-site-dropdown',
                options=[],  # Will be populated when tab loads
                placeholder="Search for a site...",
                searchable=True,
                clearable=True,
                className="mb-3"
            )
            
        ], style={'marginBottom': '20px'}),
        
        # Controls and content - hidden until site is selected
        html.Div([
            # Parameter selection - full row
            dbc.Row([
                dbc.Col([
                    html.Label("Select Chemical Parameter:", className="form-label mb-2", style={'fontWeight': 'bold', 'fontSize': '1rem'}),
                    dcc.Dropdown(
                        id='chemical-parameter-dropdown',
                        options=[
                            {'label': 'Dissolved Oxygen', 'value': 'do_percent'},
                            {'label': 'pH', 'value': 'pH'},
                            {'label': 'Nitrogen', 'value': 'soluble_nitrogen'},
                            {'label': 'Phosphorus', 'value': 'Phosphorus'},
                            {'label': 'Chloride', 'value': 'Chloride'},
                            {'label': 'All Parameters', 'value': 'all_parameters'}
                        ],
                        value=None,
                        className="mb-3"
                    )
                ], width=12)
            ]),
            
            # Year range 
            dbc.Row([
                dbc.Col([
                    html.Label("Select Year Range:", className="form-label mb-2", style={'fontWeight': 'bold', 'fontSize': '1rem'}),
                    dcc.RangeSlider(
                        id='year-range-slider',
                        min=min_year,
                        max=max_year,
                        step=1,
                        marks={year: str(year) for year in range(min_year, max_year + 1)},
                        value=[min_year, max_year],  # Show full range by default
                        className="mb-3"
                    )
                ], width=12)  
            ]),
            
            # Season and month selection - UPDATED LAYOUT TO MATCH ORIGINAL
            dbc.Row([
                dbc.Col([
                    html.Label(
                        "Select Season:", 
                        className="form-label mb-2",
                        style={"display": "inline-block", "vertical-align": "middle", "margin-right": "10px", "fontWeight": "bold", "fontSize": "1rem"}
                    ),
                    dbc.ButtonGroup(
                        [
                            dbc.Button("ALL", color="secondary", id="select-all-months", n_clicks=1, size="sm"),
                            dbc.Button("SPRING", color="success", id="select-spring", n_clicks=0, size="sm"),
                            dbc.Button("SUMMER", color="warning", id="select-summer", n_clicks=0, size="sm"),
                            dbc.Button("FALL", color="danger", id="select-fall", n_clicks=0, size="sm"),
                            dbc.Button("WINTER", color="info", id="select-winter", n_clicks=0, size="sm")
                        ],
                        style={"display": "inline-block", "vertical-align": "middle"}
                    )
                ], width=5),

                # Month selection 
                dbc.Col([
                    html.Label(
                        "Select Months:", 
                        className="form-label mb-2",
                        style={"display": "inline-block", "vertical-align": "middle", "margin-right": "10px", "fontWeight": "bold", "fontSize": "1rem"}
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
            ], className="mb-3"),
            
            # Highlight switch 
            dbc.Row([
                dbc.Col([
                    html.Label(
                        "Highlight Threshold Violations:", 
                        className="form-label mb-2",
                        style={"display": "inline-block", "vertical-align": "middle", "margin-right": "10px", "fontWeight": "bold", "fontSize": "1rem"}
                    ),
                    dbc.Switch(
                        id="highlight-thresholds-switch",
                        value=True,
                        style={"display": "inline-block", "vertical-align": "middle"}
                    )
                ], width=6)
            ], className="mb-3"),
            
            # Graph 
            dbc.Row([
                dbc.Col([
                    html.Div(id='chemical-graph-container')
                ], width=12)
            ], className="mb-2"),
            
            # Description and diagram 
            dbc.Row([
                dbc.Col([
                    html.Div(id='chemical-explanation-container')
                ], width=6, className="d-flex"),  
                dbc.Col([
                    html.Div(id='chemical-diagram-container')
                ], width=6, className="d-flex align-items-center")  
            ], className="h-100 align-items-stretch", style={'minHeight': '400px'})
        ], id="chemical-controls-content", style={'display': 'none'}),
    ], className="tab-content-wrapper") 