"""
Source Data tab layout for the Tenmile Creek Water Quality Dashboard.
"""

import dash_bootstrap_components as dbc
from dash import html
from utils import load_markdown_content
from ..constants import TAB_STYLES
from ..helpers import create_source_data_links

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