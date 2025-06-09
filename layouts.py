"""
Layout functions for the Tenmile Creek Water Quality Dashboard.
This file contains functions that create and return the layouts for different dashboard tabs.
"""

import dash_bootstrap_components as dbc
from dash import dcc, html
from data_processing.data_queries import get_chemical_date_range
from utils import load_markdown_content, create_image_with_caption, setup_logging

# Import from data_definitions to avoid duplication

# Configure logging
logger = setup_logging("layouts", category="app")

# --------------------------------------------------------------------------------------
# LAYOUT CONSTANTS
# --------------------------------------------------------------------------------------

# Overview tab parameter options
PARAMETER_OPTIONS = [
    {'label': 'Chemical: Dissolved Oxygen', 'value': 'chem:do_percent'},
    {'label': 'Chemical: pH', 'value': 'chem:pH'},
    {'label': 'Chemical: Nitrogen', 'value': 'chem:soluble_nitrogen'},
    {'label': 'Chemical: Phosphorus', 'value': 'chem:Phosphorus'},
    {'label': 'Chemical: Chloride', 'value': 'chem:Chloride'},
    {'label': 'Biological: Fish Community', 'value': 'bio:Fish_IBI'},
    {'label': 'Biological: Macroinvertebrate Community', 'value': 'bio:Macro_Combined'},
    {'label': 'Physical: Habitat Scores', 'value': 'habitat:Habitat_Score'}
]

# Chemical tab parameter options
CHEMICAL_OPTIONS = [
    {'label': 'Dissolved Oxygen', 'value': 'do_percent'},
    {'label': 'pH', 'value': 'pH'},
    {'label': 'Nitrogen', 'value': 'soluble_nitrogen'},
    {'label': 'Phosphorus', 'value': 'Phosphorus'},
    {'label': 'Chloride', 'value': 'Chloride'},
    {'label': 'All Parameters', 'value': 'all_parameters'}
]

# Biological tab parameter options
BIOLOGICAL_OPTIONS = [
    {'label': 'Fish Community', 'value': 'fish'},
    {'label': 'Macroinvertebrate Community', 'value': 'macro'},
]

# Habitat tab parameter options
HABITAT_OPTIONS = [
    {'label': 'Habitat', 'value': 'habitat'}
]

# Tab styles
TAB_STYLES = {
    "standard_margin": "mt-3",
    "small_margin": "mt-1",
    "image_container": "d-flex h-100 align-items-center justify-content-center"
}

# --------------------------------------------------------------------------------------
# HELPER FUNCTIONS
# --------------------------------------------------------------------------------------

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
        "Common fish species found in Tenmile Creek" 
        if species_type == 'fish' 
        else "Common macroinvertebrates found in Tenmile Creek"
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
            style={'min-height': '400px'}  # Fixed minimum height for whole gallery
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

def create_overview_image_section():
    """
    Create the overview image section with caption.
    
    Returns:
        A Column component with the overview image
    """
    return dbc.Col([
        html.Div([
            create_image_with_caption(
                src='/assets/images/healthy_stream_diagram.png',
                caption="The key elements of a healthy stream ecosystem include riparian vegetation, diverse aquatic life, and clean water flow."
            )
        ], className="d-flex align-items-center justify-content-center h-100 flex-column")
    ], width=6, style={"display": "flex", "align-items": "center"}) 

def create_habitat_image_section():
    """
    Create the habitat image section with caption.
    
    Returns:
        A Column component with the habitat image
    """
    return dbc.Col([
        html.Div([
            create_image_with_caption(
                src='/assets/images/stream_habitat_diagram.jpg',
                caption="The physical features evaluated during habitat assessment include stream structure, bank stability, and riparian zone components."
            )
        ], className="d-flex h-100 align-items-center justify-content-center")
    ], width=6, className="d-flex align-items-center")

def create_watershed_image_section():
    """
    Create the watershed image section with caption.
    
    Returns:
        A Column component with the watershed image
    """
    return dbc.Col([
        html.Div([
            create_image_with_caption(
                src='/assets/images/watershed_diagram.jpg',
                caption="In a watershed, water flows from higher elevations through various landscapes and eventually to streams, rivers, and lakes."
            )
        ], className="d-flex h-100 align-items-center justify-content-center flex-column")
    ], width=6, className="d-flex align-items-center")

def create_source_data_links():
    """
    Create links to source data files.
    
    Returns:
        An unordered list with links to source data files
    """
    return html.Ul([
        # Links to PDFs
        html.Li(
            html.A(
                "Tenmile Data Packet (PDF)",  
                href="/assets/source_data/Tenmile data packet.pdf",    
                target="_blank"                   
            )
        ),
        html.Li(
            html.A(
                "Data Definitions (PDF)",
                href="/assets/source_data/data definitions.pdf",
                target="_blank"
            )
        ),
        # Link to Excel data
        html.Li(
            html.A(
                "Tenmile Chemical Data (Excel)",
                href="/assets/source_data/Tenmile chemical.xlsx",
                target="_blank"
            )
        )
    ])

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

# --------------------------------------------------------------------------------------
# TAB CREATION FUNCTIONS
# --------------------------------------------------------------------------------------

def create_overview_tab():
    """
    Create the layout for the Overview tab.
    
    Returns:
        HTML layout for the Overview tab
    """
    try:
        # Create the layout WITHOUT creating the map
        tab_content = html.Div([
            # First row: Overview text and image
            dbc.Row([
                # Left column for text 
                dbc.Col([
                    load_markdown_content('overview/overview.md')
                ], width=6),
                
                # Right column for image 
                create_overview_image_section()
            ]),
            
            # Second row: Monitoring Site Locations section
            dbc.Row([
                dbc.Col([
                    html.H3("Monitoring Site Locations", className="mt-4 mb-3"),
                    load_markdown_content('overview/monitoring_sites.md')
                ], width=12)
            ]),
            
            # Third row: Parameter selection dropdown
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

            # Fourth row: Active sites toggle - UPDATED TO MATCH CHEMICAL TAB STYLING
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
            
            # Fifth row: Map (empty initially, filled by callback)
            dbc.Row([
                dbc.Col([
                    dcc.Graph(
                        id='site-map-graph',
                        figure={},  # Empty figure - callback will populate
                        config={
                            'scrollZoom': True,
                            'displayModeBar': True,
                            'modeBarButtonsToRemove': ['lasso2d', 'select2d']
                        }
                    )
                ], width=12)
            ]),
            
            # Sixth row: Dynamic Legend Container
            dbc.Row([
                dbc.Col([
                    html.Div(id='map-legend-container', className="text-center mt-2 mb-4")
                ], width=12)
            ])
        ], className=TAB_STYLES["standard_margin"])
        
        return tab_content
        
    except Exception as e:
        print(f"Error creating overview tab: {e}")
        return html.Div([
            html.Div("Error loading overview tab content", className="alert alert-danger"),
            html.Pre(str(e), style={"fontSize": "12px"})
        ])

def create_chemical_tab():
    """Create the chemical data tab layout with simple search functionality."""

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
        
        # Site search section
        html.Div([
            html.Label("Select Site:", className="form-label mb-2", style={'fontWeight': 'bold'}),
            
            # Helper text
            html.Small(
                "Enter a search term and click 'Search' or press enter to find monitoring sites",
                className="text-muted mb-2 d-block"
            ),

            # Search input with button
            html.Div([
                dbc.InputGroup([
                    dbc.Input(
                        id='chemical-search-input',
                        placeholder="Enter site name (e.g., Tenmile, Boggy, Blue)",
                        type="text",
                        value="",
                        n_submit=0
                    ),
                    dbc.Button(
                        "Search",
                        id='chemical-search-button',
                        color="primary",
                        n_clicks=0
                    ),
                    dbc.Button(
                        "Clear",
                        id='chemical-clear-button',
                        color="secondary",
                        n_clicks=0
                    )
                ])
            ], style={'position': 'relative', 'marginBottom': '5px'}),
            
            # Search results list (initially hidden)
            html.Div(
                id='chemical-search-results',
                children=[],
            ),
            
            # Hidden store for selected site
            dcc.Store(id='chemical-selected-site', data=None)
            
        ], style={'position': 'relative', 'marginBottom': '20px'}),
        
        # Controls and content - hidden until site is selected
        html.Div([
            # Parameter selection - full row
            dbc.Row([
                dbc.Col([
                    html.Label("Select Chemical Parameter:", className="form-label mb-2", style={'fontWeight': 'bold'}),
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
                        value='do_percent',
                        className="mb-3"
                    )
                ], width=12)
            ]),
            
            # Year range 
            dbc.Row([
                dbc.Col([
                    html.Label("Select Year Range:", className="form-label mb-2", style={'fontWeight': 'bold'}),
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
                        style={"display": "inline-block", "vertical-align": "middle", "margin-right": "10px", "fontWeight": "bold"}
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
                        style={"display": "inline-block", "vertical-align": "middle", "margin-right": "10px", "fontWeight": "bold"}
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
                        style={"display": "inline-block", "vertical-align": "middle", "margin-right": "10px", "fontWeight": "bold"}
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
            ], className="mb-4"),
            
            # Description and diagram 
            dbc.Row([
                dbc.Col([
                    html.Div(id='chemical-explanation-container')
                ], width=6, className="d-flex"),  
                dbc.Col([
                    html.Div(id='chemical-diagram-container')
                ], width=6, className="d-flex align-items-center")  
            ], className="h-100 align-items-stretch", style={'minHeight': '400px'})
        ], id="chemical-controls-content", style={'display': 'none'})
    ])

def create_biological_tab():
    """Create the biological data tab layout with community-first selection."""
    return html.Div([
        # Description - always visible
        html.Div([
            html.P([
                load_markdown_content('biological/biological_intro.md')
            ]),
            html.P([
                "Select a community type and search for a site below to begin analysis."
                "You can find site names and locations on the ",
                html.A("Overview tab.", id="biological-overview-link", href="#", style={"text-decoration": "underline"}),
                
            ])
        ], className="mb-4"),
        
        # Community selection - always visible
        html.Div([
            html.Label("Select Biological Community:", className="form-label mb-2", style={'fontWeight': 'bold'}),
            dcc.Dropdown(
                id='biological-community-dropdown',
                options=[
                    {'label': 'Select a community type...', 'value': '', 'disabled': True},
                    {'label': 'Fish Community', 'value': 'fish'},
                    {'label': 'Macroinvertebrate Community', 'value': 'macro'}
                ],
                value='',  # Start with no selection
                placeholder="Choose a biological community",
                className="mb-3"
            )
        ], className="mb-4"),
        
        # Site search section - hidden until community is selected
        html.Div([
            html.Label("Select Site:", className="form-label mb-2", style={'fontWeight': 'bold'}),
            
            # Helper text
            html.Small(
                "Enter a search term and click 'Search' or press enter to find monitoring sites",
                className="text-muted mb-2 d-block"
            ),

            # Search input with button
            html.Div([
                dbc.InputGroup([
                    dbc.Input(
                        id='biological-search-input',
                        placeholder="Enter site name (e.g., Tenmile, Boggy, Blue)",
                        type="text",
                        value="",
                        disabled=True,  # Start disabled
                        n_submit=0
                    ),
                    dbc.Button(
                        "Search",
                        id='biological-search-button',
                        color="primary",
                        n_clicks=0,
                        disabled=True  # Start disabled
                    ),
                    dbc.Button(
                        "Clear",
                        id='biological-clear-button',
                        color="secondary",
                        n_clicks=0,
                        disabled=True  # Start disabled
                    )
                ])
            ], style={'position': 'relative', 'marginBottom': '5px'}),
            
            # Search results list (initially hidden)
            html.Div(
                id='biological-search-results',
                children=[],
            ),
            
            # Hidden store for selected site
            dcc.Store(id='biological-selected-site', data=None)
            
        ], id='biological-site-search-section', style={'display': 'none', 'position': 'relative', 'marginBottom': '20px'}),
        
        # Content container - shows biological data after both selections are made
        html.Div(id='biological-content-container', className="mt-4"),
        
        # Legacy controls content section - keeping for compatibility with existing callbacks
        html.Div(id="biological-controls-content", style={'display': 'none'})
    ])

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

def create_protect_our_streams_tab():
    """
    Create the layout for the Protect Our Streams tab.
    
    Returns:
        HTML layout for the Protect Our Streams tab
    """
    try:
        # Import the card data
        from config.action_cards import HOME_YARD_CARDS, RURAL_CARDS, RECREATION_CARDS, COMMUNITY_CARDS
        
        # Create cards using the imported data
        home_yard_cards = [create_action_card(**card) for card in HOME_YARD_CARDS]
        rural_cards = [create_action_card(**card) for card in RURAL_CARDS]
        recreation_cards = [create_action_card(**card) for card in RECREATION_CARDS]
        community_cards = [create_action_card(**card) for card in COMMUNITY_CARDS]
        
        # Create main tabs with all cards displayed for each category
        main_tabs = dbc.Tabs([
            dbc.Tab(
                dbc.Row([
                    *[dbc.Col(card, width=12, md=6, lg=4, className="mb-4") for card in home_yard_cards]
                ], className="mt-3"),
                label="Home & Yard"
            ),
            dbc.Tab(
                dbc.Row([
                    *[dbc.Col(card, width=12, md=6, lg=4, className="mb-4") for card in rural_cards]
                ], className="mt-3"),
                label="Rural & Agricultural"
            ),
            dbc.Tab(
                dbc.Row([
                    *[dbc.Col(card, width=12, md=6, lg=4, className="mb-4") for card in recreation_cards]
                ], className="mt-3"),
                label="Recreation"
            ),
            dbc.Tab(
                dbc.Row([
                    *[dbc.Col(card, width=12, md=6, lg=4, className="mb-4") for card in community_cards]
                ], className="mt-3"),
                label="Community Action"
            )
        ], className="mt-4")
            
        # Put everything together in the tab layout
        tab_content = html.Div([
            # First row with text and image side by side
            dbc.Row([
                # Left column for text 
                dbc.Col([
                    load_markdown_content('protect_our_streams_intro.md')
                ], width=6),
                
                # Right column for image 
                create_watershed_image_section()
            ]),
            
            # Second row for "Actions You Can Take" section
            dbc.Row([
                dbc.Col([
                    html.H3("Actions You Can Take", className="mt-4"),
                    main_tabs
                ], width=12)
            ])
        ], className=TAB_STYLES["standard_margin"])
        
        return tab_content
        
    except Exception as e:
        print(f"Error creating protect our streams tab: {e}")
        return html.Div([
            html.Div("Error loading protect our streams tab content", className="alert alert-danger"),
            html.Pre(str(e), style={"fontSize": "12px"})
        ])

def create_source_data_tab():
    """
    Create the layout for the Source Data tab.
    
    Returns:
        HTML layout for the Source Data tab
    """
    try:
        tab_content = html.Div([
            dbc.Row([
                dbc.Col([
                    load_markdown_content('source_data.md'),
                    create_source_data_links()
                ], width=12)
            ])
        ], className=TAB_STYLES["standard_margin"])
        
        return tab_content
        
    except Exception as e:
        print(f"Error creating source data tab: {e}")
        return html.Div([
            html.Div("Error loading source data tab content", className="alert alert-danger"),
            html.Pre(str(e), style={"fontSize": "12px"})
        ])

# --------------------------------------------------------------------------------------
# MODAL CREATION FUNCTIONS
# --------------------------------------------------------------------------------------

def create_icon_attribution_modal():
    """
    Create the attribution modal for icon credits.
    
    Returns:
        Modal component for icon attribution
    """
    return dbc.Modal(
        [
            dbc.ModalHeader("Icon Attribution"),
            dbc.ModalBody([
                html.P("Icons made by:"),
                html.Ul([
                    html.Li([html.A("Prashanth Rapolu", href="https://www.flaticon.com/authors/prashanth-rapolu", target="_blank")]),
                    html.Li([html.A("Freepik", href="https://www.freepik.com", target="_blank")]),
                    html.Li([html.A("Eucalyp", href="https://www.flaticon.com/authors/eucalyp", target="_blank")]),
                    html.Li([html.A("Elzicon", href="https://www.flaticon.com/authors/elzicon", target="_blank")]),
                    html.Li([html.A("Flat Icons", href="https://www.flaticon.com/authors/flat-icons", target="_blank")]),
                    html.Li([html.A("Iconjam", href="https://www.flaticon.com/authors/iconjam", target="_blank")]),
                    html.Li([html.A("Three Musketeers", href="https://www.flaticon.com/authors/three-musketeers", target="_blank")]),
                    html.Li([html.A("nangicon", href="https://www.flaticon.com/authors/nangicon", target="_blank")]),
                    html.Li([html.A("Slamlabs", href="https://www.flaticon.com/authors/slamlabs", target="_blank")]),
                    html.Li([html.A("Good Ware", href="https://www.flaticon.com/authors/good-ware", target="_blank")])
                ]),
                html.P([
                    "All icons from ",
                    html.A("www.flaticon.com", href="https://www.flaticon.com", target="_blank")
                ])
            ]),
            dbc.ModalFooter(
                dbc.Button("Close", id="close-attribution", className="ml-auto")
            ),
        ],
        id="attribution-modal",
    )

def create_image_credits_modal():
    """
    Create the modal for image credits.
    
    Returns:
        Modal component for image credits
    """
    # Image sources and attributions
    image_sources = [
        ("Stream Habitat Diagram", "Engaging Bellevue", 
         "https://www.engagingbellevue.com/watershed-management/news_feed/watershed-map"),
        ("Dissolved Oxygen Graphic", "Queen Mary University of London", 
         "https://www.qmul.ac.uk/chesswatch/water-quality-sensors/dissolved-oxygen/"),
        ("pH Scale Graphic", "Water Rangers", 
         "https://waterrangers.com/test/educational-resources/lessons/ph-and-alkalinity/?v=0b3b97fa6688"),
        ("Nitrogen Cycle Diagram", "Francodex", 
         "https://www.francodex.com/en/our-veterinary-advice/nitrogen-cycle"),
        ("Phosphorus Cycle Diagram", "IISD Experiemental Lakes Area", 
         "https://www.iisd.org/ela/blog/back-to-basics-how-and-why-phosphorus-cycles-through-a-lake/"),
        ("Chloride Graphic", "LWV Upper Mississippi River Region", 
         "https://www.lwvumrr.org/blog/a-view-from-illinois-minnesota-and-wisconson-on-saltwise-and-saltsmart-practices"),
        ("Bluegill Sunfish Image", "Wired2fish", 
         "https://www.wired2fish.com/crappie-fishing/bluegill-sunfish-a-comprehensive-species-guide"),
        ("Redfin Shiner Image", "Iowa Department of Natural Resources", 
         "https://programs.iowadnr.gov/bionet/Fish/Species/27"),
        ("Mosquitofish Image", "Wikipedia", 
         "https://en.wikipedia.org/wiki/Mosquitofish"),
        ("Longear Sunfish Image", "Illinois Department of Natural Resources", 
         "https://dnr.illinois.gov/education/wildaboutpages/wildaboutfishes/wafsunfish/waflongearsunfish.html"),
        ("Caddisfly Image", "Britannica", 
         "https://www.britannica.com/animal/caddisfly"),
        ("Non-biting-midge image", "iNaturalist", 
         "https://www.inaturalist.org/guide_taxa/925163"),
        ("Riffle Beetle Image", "iNaturalist", 
         "https://www.inaturalist.org/guide_taxa/262353"),
        ("Stonefly Image", "Pensoft Blog", 
         "https://blog.pensoft.net/2015/11/09/how-did-the-stonefly-cross-the-lake-the-mystery-of-stoneflies-recolonising-a-us-island/"),
        ("Stream Habitat Diagram", "Texas Aquatic Science", 
         "https://texasaquaticscience.org/streams-and-rivers-aquatic-science-texas/"),
        ("Watershed Diagram", "Snohomish Conservation District", 
         "https://snohomishcd.org/whats-a-watershed")
    ]
    
    # Create list items for each image source
    image_credits_list = [
        html.Li([
            f"{name}: ", 
            html.A(source, href=url, target="_blank")
        ]) for name, source, url in image_sources
    ]
    
    return dbc.Modal(
        [
            dbc.ModalHeader("Image Credits"),
            dbc.ModalBody([
                html.P("This dashboard uses the following images for educational purposes:"),
                html.Ul(image_credits_list),
                html.P([
                    "All images are used for non-commercial educational purposes. ",
                    "If you are a copyright owner and would like an image removed, ",
                    "please contact us."
                ])
            ]),
            dbc.ModalFooter(
                dbc.Button("Close", id="close-image-credits", className="ml-auto")
            ),
        ],
        id="image-credits-modal",
        size="lg"
    )