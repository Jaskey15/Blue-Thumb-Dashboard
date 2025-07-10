"""
Callbacks for the chatbot functionality
"""

import os
from datetime import datetime

import dash
import dash_bootstrap_components as dbc
from dash import MATCH, Input, Output, State, html
from google import genai
from google.genai import types

from utils import setup_logging

logger = setup_logging("chatbot_callbacks", category="callbacks")

# --- Model Configuration ---
PROJECT_ID = os.environ.get('GOOGLE_CLOUD_PROJECT')
LOCATION = "global" 
CHAT_MODEL_NAME = "gemini-2.0-flash-001"
DATA_STORE_ID = "blue-thumb-context-docs-ds_1751833049776"
DATA_STORE_LOCATION = "us"
MAX_TOKENS = 1024
TEMPERATURE = 0.3

# --- Client Initialization ---
client = genai.Client(
    vertexai=True,
    project=PROJECT_ID,
    location=LOCATION,
)

# --- Tool and System Instruction Configuration ---
data_store_path = ("projects/blue-thumb-dashboard/locations/us/collections/default_collection/dataStores/blue-thumb-context-docs-ds_1751833049776")
grounding_tool = types.Tool(retrieval=types.Retrieval(vertex_ai_search=types.VertexAISearch(datastore=data_store_path)))
google_search_tool = types.Tool(google_search=types.GoogleSearch())

system_instruction = """You are a helpful stream health expert. Your main goal is to answer questions about water quality and aquatic ecosystems. 
                        Base your answers on the provided documents from the data store first. If you cannot find the answer in the documents, use Google Search. 
                        All answers should be framed through the lens of stream health. IMPORTANT: Keep responses concise and to the point, ideally 2-4 sentences. 
                        Avoid unnecessary detail unless asked. Always end with complete sentences - never cut off mid-thought."""

def format_message(text, is_user=True, timestamp=None, is_typing=False):
    """Format a chat message with appropriate styling and an avatar."""
    if timestamp is None:
        timestamp = datetime.now().strftime("%I:%M %p")

    avatar_src = "/assets/icons/user_icon.png" if is_user else "/assets/images/blue_thumb_logo.png"
    message_class = "user-message-row" if is_user else "assistant-message-row"

    avatar = html.Img(src=avatar_src, className="chat-avatar")

    if is_typing:
        message_bubble = html.Div(
            dbc.Spinner(size="sm", color="secondary"),
            className="chat-message assistant-message typing-indicator"
        )
    else:
        message_bubble = html.Div(
            text,
            className=f"chat-message {'user-message' if is_user else 'assistant-message'}"
        )
    
    if is_user:
        content = [message_bubble, avatar]
    else:
        content = [avatar, message_bubble]

    return html.Div([
        html.Div(content, className=f"chat-row {message_class}"),
        html.Div(
            timestamp,
            className=f"chat-timestamp {'user-timestamp' if is_user else 'assistant-timestamp'}"
        )
    ])

def register_chatbot_callbacks(app):
    @app.callback(
        Output({"type": "chat-collapse", "tab": MATCH}, "is_open"),
        [Input({"type": "chat-toggle", "tab": MATCH}, "n_clicks"),
         Input({"type": "chat-close", "tab": MATCH}, "n_clicks")],
        [State({"type": "chat-collapse", "tab": MATCH}, "is_open")],
        prevent_initial_call=True
    )
    def toggle_chat_collapse(toggle_clicks, close_clicks, is_open):
        """Toggle the chat panel open/closed"""
        if toggle_clicks is None and close_clicks is None:
            return is_open
        return not is_open

    @app.callback(
        Output({'type': 'chat-callout', 'tab': MATCH}, 'style'),
        [Input({'type': 'chat-callout-interval', 'tab': MATCH}, 'n_intervals'),
         Input({"type": "chat-toggle", "tab": MATCH}, "n_clicks")],
        prevent_initial_call=True
    )
    def hide_chat_callout(n_intervals, n_clicks):
        """Hide the chat callout after a delay or on click."""
        return {'display': 'none'}

    @app.callback(
        [Output({"type": "chat-messages", "tab": MATCH}, "children", allow_duplicate=True),
         Output({"type": "chat-input", "tab": MATCH}, "value"),
         Output({'type': 'chat-request-store', 'tab': MATCH}, 'data')],
        [Input({"type": "chat-submit", "tab": MATCH}, "n_clicks"),
         Input({"type": "chat-input", "tab": MATCH}, "n_submit")],
        [State({"type": "chat-input", "tab": MATCH}, "value"),
         State({"type": "chat-messages", "tab": MATCH}, "children")],
        prevent_initial_call=True
    )
    def display_user_message_and_trigger_response(
        n_clicks, n_submit, message, existing_messages
    ):
        """
        Display the user's message immediately and trigger the AI response.
        """
        if (n_clicks is None and n_submit is None) or not message:
            return existing_messages or [], "", dash.no_update

        if existing_messages is None:
            existing_messages = []

        # Add user message
        existing_messages.append(format_message(message, is_user=True))
        # Add typing indicator
        existing_messages.append(format_message("", is_user=False, is_typing=True))

        # Store the user's message to trigger the next callback
        request_data = {'message': message}
        
        return existing_messages, "", request_data

    @app.callback(
        Output({"type": "chat-messages", "tab": MATCH}, "children", allow_duplicate=True),
        Input({'type': 'chat-request-store', 'tab': MATCH}, 'data'),
        State({"type": "chat-messages", "tab": MATCH}, "children"),
        prevent_initial_call=True
    )
    def fetch_assistant_response(request_data, existing_messages):
        """
        Fetch the AI response and update the chat, replacing the indicator.
        """
        if not request_data or 'message' not in request_data:
            return dash.no_update

        message = request_data['message']
        logger.info(f"Received user query: {message}")

        try:
            # Configure generation settings
            generation_config = types.GenerateContentConfig(
                temperature=TEMPERATURE,
                top_p=1,
                max_output_tokens=MAX_TOKENS,
                safety_settings=[
                    types.SafetySetting(
                        category="HARM_CATEGORY_HATE_SPEECH",
                        threshold="BLOCK_ONLY_HIGH"
                    ),
                    types.SafetySetting(
                        category="HARM_CATEGORY_DANGEROUS_CONTENT",
                        threshold="BLOCK_ONLY_HIGH"
                    ),
                    types.SafetySetting(
                        category="HARM_CATEGORY_SEXUALLY_EXPLICIT",
                        threshold="BLOCK_ONLY_HIGH"
                    ),
                    types.SafetySetting(
                        category="HARM_CATEGORY_HARASSMENT",
                        threshold="BLOCK_ONLY_HIGH"
                    )
                ],
                tools=[grounding_tool, google_search_tool],
                system_instruction=[types.Part.from_text(text=system_instruction)],
            )

            # Generate content using the new client
            response = client.models.generate_content(
                model=CHAT_MODEL_NAME,
                contents=[message],
                config=generation_config,
            )

            if response.candidates and response.candidates[0].grounding_metadata:
                logger.info("Response was grounded.")
            else:
                logger.info("Response was not grounded.")

            assistant_message = response.text

            # Check for truncation
            if response.candidates and response.candidates[0].finish_reason.name == "MAX_TOKENS":
                assistant_message += "\n\n[Response truncated due to length. Ask me for more specific details if needed.]"

        except ValueError:
            assistant_message = "I received your question but I'm having trouble formatting my response. Could you try rephrasing your question?"
            logger.warning(
                f"Response object exists but couldn't extract text content."
            )
        except Exception as e:
            assistant_message = "I apologize, but I'm having trouble responding right now. Please try again."
            logger.error(f"Error in chat response: {e}", exc_info=True)
            
        logger.info(f"Sending assistant response: {assistant_message}")

        # Replace the typing indicator with the actual response
        if existing_messages and len(existing_messages) > 0:
            existing_messages[-1] = format_message(
                assistant_message, is_user=False
            )

        return existing_messages

    # This clientside callback handles auto-scrolling
    app.clientside_callback(
        """
        function(children) {
            // Give a brief moment for the DOM to update
            setTimeout(function() {
                try {
                    const elements = document.querySelectorAll('.chat-messages-container');
                    // Find the one visible element and scroll it
                    for (let i = 0; i < elements.length; i++) {
                        const element = elements[i];
                        // offsetParent is null for hidden elements
                        if (element.offsetParent !== null) {
                            element.scrollTop = element.scrollHeight;
                            break; // Exit after scrolling the first visible one
                        }
                    }
                } catch (e) {
                    console.error("Error scrolling chat:", e);
                }
            }, 50);
            return window.dash_clientside.no_update;
        }
        """,
        # A dummy output is required for clientside callbacks
        Output({'type': 'chat-scroll-store', 'tab': MATCH}, 'data'),
        Input({'type': 'chat-messages', 'tab': MATCH}, 'children'),
        prevent_initial_call=True
    ) 