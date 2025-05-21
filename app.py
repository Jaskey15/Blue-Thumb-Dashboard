import dash
import dash_bootstrap_components as dbc

from callbacks import register_callbacks
from dash import html
from layouts import (
    create_overview_tab, create_chemical_tab, create_biological_tab,
    create_habitat_tab, create_protect_our_streams_tab, create_source_data_tab,
    create_icon_attribution_modal, create_image_credits_modal
)

# Initialize the Dash app
app = dash.Dash(__name__, 
                external_stylesheets=[dbc.themes.SANDSTONE],
                suppress_callback_exceptions=True)
server = app.server

# Define header 
header = dbc.Container([
    dbc.Row([
        dbc.Col(
            html.Div([
                html.H1("Blue Thumb Stream Health Dashboard", 
                       className="text-white text-center p-3",
                       style={
                           'font-size': '2.5rem',  
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
        dbc.Tab(label="Overview", children=create_overview_tab()),
        dbc.Tab(label="Chemical Data", children=create_chemical_tab()),
        dbc.Tab(label="Biological Data", children=create_biological_tab()),
        dbc.Tab(label="Habitat Data", children=create_habitat_tab()),
        dbc.Tab(label="Protect Our Streams", children=create_protect_our_streams_tab()),
        dbc.Tab(label="Source Data", children=create_source_data_tab()),
    ]),

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