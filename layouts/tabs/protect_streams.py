"""
Protect Our Streams tab layout for the Tenmile Creek Water Quality Dashboard.
"""

import dash_bootstrap_components as dbc
from dash import html
from utils import load_markdown_content, create_image_with_caption
from ..constants import TAB_STYLES
from ..helpers import create_action_card

def create_protect_our_streams_tab():
    """
    Create the layout for the Protect Our Streams tab.
    
    Returns:
        HTML layout for the Protect Our Streams tab
    """
    try:
        # Import the card data
        from ..ui_data import HOME_YARD_CARDS, RURAL_CARDS, RECREATION_CARDS, COMMUNITY_CARDS
        
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
                    load_markdown_content('protect_our_streams_intro.md', link_target="_blank")
                ], width=6),
                
                # Right column for image 
                dbc.Col([
                    html.Div([
                        create_image_with_caption(
                            src='/assets/images/watershed_diagram.jpg',
                            caption="In a watershed, water flows from higher elevations through various landscapes and eventually to streams, rivers, and lakes."
                        )
                    ], className="d-flex h-100 align-items-center justify-content-center flex-column tab-image-container")
                ], width=6, className="d-flex align-items-center")
            ]),
            
            # Second row for "Actions You Can Take" section
            dbc.Row([
                dbc.Col([
                    html.H3("Actions You Can Take"),
                    main_tabs
                ], width=12)
            ])
        ], className="tab-content-wrapper")
        
        return tab_content
        
    except Exception as e:
        print(f"Error creating protect our streams tab: {e}")
        return html.Div([
            html.Div("Error loading protect our streams tab content", className="alert alert-danger"),
            html.Pre(str(e), style={"fontSize": "12px"})
        ]) 