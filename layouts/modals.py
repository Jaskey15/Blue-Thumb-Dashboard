"""
Modal creation functions for the dashboard
"""

import dash_bootstrap_components as dbc
from dash import html


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
                    html.Li([html.A("Good Ware", href="https://www.flaticon.com/authors/good-ware", target="_blank")]),
                    html.Li([html.A("Catkuro", href="https://www.flaticon.com/free-icons/report", target="_blank")]),
                    html.Li([html.A("Hajicon", href="https://www.flaticon.com/free-icons/analysis", target="_blank")])
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
        ("Macroinvertebrate Images", "iNaturalist", 
         "https://www.inaturalist.org/"),
        ("Stream Habitat Diagram", "Texas Aquatic Science", 
         "https://texasaquaticscience.org/streams-and-rivers-aquatic-science-texas/"),
        ("Watershed Diagram", "Snohomish Conservation District", 
         "https://snohomishcd.org/whats-a-watershed")
    ]
    
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