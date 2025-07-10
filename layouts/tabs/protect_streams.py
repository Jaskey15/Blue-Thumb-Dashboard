"""
Protect Our Streams tab layout for the dashboard
"""

import dash_bootstrap_components as dbc
from dash import html

from utils import create_image_with_caption, load_markdown_content

from ..components.chatbot import create_floating_chatbot
from ..helpers import create_action_card
from ..ui_data import COMMUNITY_CARDS, HOME_YARD_CARDS, RECREATION_CARDS, RURAL_CARDS


def create_protect_our_streams_tab():
    """
    Create the layout for the Protect Our Streams tab.
    
    Returns:
        HTML layout for the Protect Our Streams tab
    """
    try:
        # Create action cards for each category
        home_yard_cards = [create_action_card(**card) for card in HOME_YARD_CARDS]
        rural_cards = [create_action_card(**card) for card in RURAL_CARDS]
        recreation_cards = [create_action_card(**card) for card in RECREATION_CARDS]
        community_cards = [create_action_card(**card) for card in COMMUNITY_CARDS]
        
        # Create tabbed interface for action categories
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
            
        tab_content = html.Div([
            # Introduction section with text and watershed diagram
            dbc.Row([
                dbc.Col([
                    load_markdown_content('protect_our_streams_intro.md', link_target="_blank")
                ], width=6),
                
                dbc.Col([
                    html.Div([
                        create_image_with_caption(
                            src='/assets/images/watershed_diagram.jpg',
                            caption="In a watershed, water flows from higher elevations through various landscapes and eventually to streams, rivers, and lakes."
                        )
                    ], className="d-flex h-100 align-items-center justify-content-center flex-column tab-image-container")
                ], width=6, className="d-flex align-items-center")
            ], className="mobile-stack"),
            
            # Action cards section
            dbc.Row([
                dbc.Col([
                    html.H3("Actions You Can Take"),
                    main_tabs
                ], width=12)
            ])
        ], className="tab-content-wrapper")
        
        return html.Div([
            tab_content,
            create_floating_chatbot('protect_streams')
        ])
        
    except Exception as e:
        print(f"Error creating protect our streams tab: {e}")
        return html.Div([
            html.Div("Error loading protect our streams tab content", className="alert alert-danger"),
            html.Pre(str(e), style={"fontSize": "12px"})
        ]) 