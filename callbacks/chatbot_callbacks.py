"""
Callbacks for the chatbot functionality
"""

from dash import Input, Output, State, callback, html, MATCH
import dash_bootstrap_components as dbc
from datetime import datetime
import os
import json

import vertexai
from vertexai.generative_models import GenerativeModel, Tool

# model configuration
PROJECT_ID = os.environ.get('GOOGLE_CLOUD_PROJECT')
LOCATION = "us-central1" # Or any other supported region
CHAT_MODEL_NAME = "gemini-2.0-flash-lite-001"
MAX_TOKENS = 250  # Limit response length
TEMPERATURE = 0.7  # Balance between creativity and consistency

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
        html.Div(timestamp, className=f"chat-timestamp {'user-timestamp' if is_user else 'assistant-timestamp'}")
    ])

def load_all_context():
    """Load and combine all .md files from the /text directory."""
    full_context = []
    text_dir = 'text'
    for root, _, files in os.walk(text_dir):
        for file in files:
            if file.endswith('.md'):
                try:
                    with open(os.path.join(root, file), 'r', encoding='utf-8') as f:
                        # Add a separator to distinguish between file contents
                        full_context.append(f"--- START OF {file} ---\n{f.read()}\n--- END OF {file} ---\n")
                except Exception as e:
                    print(f"Error loading context from {file}: {e}")
    return "\n".join(full_context)

FULL_CONTEXT = load_all_context()

# Initialize Vertex AI
vertexai.init(project=PROJECT_ID, location=LOCATION)

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
    def display_user_message_and_trigger_response(n_clicks, n_submit, message, existing_messages):
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

        try:
            system_prompt = [f"""You are a helpful stream health expert. Your main goal is to answer 
                                questions about water quality and aquatic ecosystems.
                                Base your answers on the provided context documents. You may supplement 
                                this information with web searches to provide more detail or for topics not covered 
                                in the documents. All answers should be framed through the lens of stream health.
                                Context:
                                {FULL_CONTEXT}
                            """]

            model = GenerativeModel(
                CHAT_MODEL_NAME,
                system_instruction=system_prompt
            )
            
            google_search_tool = Tool.from_google_search_retrieval()

            response = model.generate_content(
                message,
                tools=[google_search_tool],
                generation_config={
                    "max_output_tokens": MAX_TOKENS,
                    "temperature": TEMPERATURE
                }
            )
            
            assistant_message = response.text
            
        except Exception as e:
            assistant_message = "I apologize, but I'm having trouble responding right now. Please try again."
            # Use a more robust logger to ensure the message is captured
            import logging
            logging.error(f"Error in chat response: {e}", exc_info=True)
        
        # Replace the typing indicator with the actual response
        if existing_messages and len(existing_messages) > 0:
            existing_messages[-1] = format_message(assistant_message, is_user=False)
        
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