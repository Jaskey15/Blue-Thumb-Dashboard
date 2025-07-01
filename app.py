import dash
import dash_bootstrap_components as dbc
from whitenoise import WhiteNoise

from callbacks import register_callbacks
from dash import html, dcc
from layouts.tabs.overview import create_overview_tab
from layouts.tabs.chemical import create_chemical_tab
from layouts.tabs.biological import create_biological_tab
from layouts.tabs.habitat import create_habitat_tab
from layouts.tabs.protect_streams import create_protect_our_streams_tab
from layouts.tabs.source_data import create_source_data_tab
from layouts.modals import create_icon_attribution_modal, create_image_credits_modal

# Initialize the Dash app
app = dash.Dash(__name__, 
                external_stylesheets=[dbc.themes.SANDSTONE],
                suppress_callback_exceptions=True,
                meta_tags=[
                    {"name": "viewport", "content": "width=device-width, initial-scale=1, shrink-to-fit=no"}
                ])
server = app.server

# Add WhiteNoise for serving static files on Heroku
# Configure WhiteNoise to serve assets from the root with proper URL mapping
server.wsgi_app = WhiteNoise(
    server.wsgi_app,
    root='.',  # Serve from project root
    prefix=None  # No prefix modification
)
# Add specific asset directory mapping
server.wsgi_app.add_files('assets/', prefix='assets/')

# Define header 
header = dbc.Container([
    dbc.Row([
        dbc.Col(
            html.Div([
                html.H1("Blue Thumb Stream Health Dashboard", 
                       className="text-white text-center p-3",
                       style={
                           'font-size': 'clamp(1.5rem, 4vw, 2.5rem)',  # Responsive font size
                           'font-family': 'Montserrat, sans-serif',  
                           'font-weight': '700', 
                           'text-shadow': '2px 2px 4px rgba(0, 0, 0, 0.5)', 
                           'letter-spacing': '0.5px' 
                       })
            ], 
            style={
                'background-image': 'linear-gradient(rgba(0, 0, 0, 0.5), rgba(0, 0, 0, 0.5)), url("/assets/images/header_image.png")',  
                'background-size': 'cover',
                'background-position': 'center',
                'border-radius': '5px',
                'height': '200px',
                'display': 'flex',
                'align-items': 'center',
                'justify-content': 'center'
            }),
            width=12
        )
    ])
])

# Define the layout with tabs
app.layout = dbc.Container([
    # Include the header
    header,
    
    # Tabs with modular layout functions
    dbc.Tabs([
        dbc.Tab(label="Overview", children=create_overview_tab(), tab_id="overview-tab"),
        dbc.Tab(label="Chemical Data", children=create_chemical_tab(), tab_id="chemical-tab"),
        dbc.Tab(label="Biological Data", children=create_biological_tab(), tab_id="biological-tab"),
        dbc.Tab(label="Habitat Data", children=create_habitat_tab(), tab_id="habitat-tab"),
        dbc.Tab(label="Protect Our Streams", children=create_protect_our_streams_tab(), tab_id="protect-tab"),
        dbc.Tab(label="Source Data", children=create_source_data_tab(), tab_id="source-tab"),
    ], id="main-tabs", active_tab="overview-tab"),

   
    html.Div([
         # Navigation store for map-to-tab navigation
        dcc.Store(id='navigation-store', storage_type='memory', data={'target_tab': None, 'target_site': None}),
        # Tab state stores for preserving user selections
        dcc.Store(id='overview-tab-state', storage_type='session', data={'selected_parameter': None, 'active_sites_only': False}),
        dcc.Store(id='habitat-tab-state', storage_type='session', data={'selected_site': None}),
        dcc.Store(id='biological-tab-state', storage_type='session', data={'selected_community': None, 'selected_site': None}),
        dcc.Store(id='chemical-tab-state', storage_type='session', data={
            'selected_site': None,
            'selected_parameter': None,
            'year_range': None,
            'selected_months': None,
            'highlight_thresholds': None
        })
    ], style={'display': 'none'}),

    # Footer with improved credits and logo
    dbc.Row([
        dbc.Col([
            html.Div([
                # Blue Thumb logo on the left
                html.Img(
                    src="/assets/images/blue_thumb_logo.png",
                    height="60px",  # Adjust height as needed
                    style={"margin-right": "15px", "vertical-align": "middle"}
                ),
                # Text credits on the right
                html.Span([
                    "Data source: Blue Thumb Volunteer Monitoring Program | ",
                    "Map data © Esri | ",  
                    html.A("Icons from Flaticon", href="#", id="attribution-link"), " | ",
                    html.A("Image Credits", href="#", id="image-credits-link")
                ], style={"display": "inline-block", "vertical-align": "middle"})
            ], className="text-center mt-4 text-muted d-flex align-items-center justify-content-center")
        ], width=12)
    ]),

    # Attribution modals
    create_icon_attribution_modal(),
    create_image_credits_modal()
    
], fluid=True, className="px-4", style={"max-width": "1200px", "margin": "0 auto"})

# Register callbacks
register_callbacks(app)

# Run the app
if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 8050))  # Default to 8050 if not provided
    app.run(host='0.0.0.0', port=port, debug=False)