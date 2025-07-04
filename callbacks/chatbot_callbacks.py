"""
Callbacks for the chatbot functionality
"""

from dash import Input, Output, State, callback, html, MATCH
import dash_bootstrap_components as dbc
from datetime import datetime
import openai
import os
import json

# model configuration
CHAT_MODEL = "gpt-4.1-nano"
MAX_TOKENS = 150  # Limit response length
TEMPERATURE = 0.7  # Balance between creativity and consistency

def format_message(text, is_user=True, timestamp=None):
    """Format a chat message with appropriate styling and an avatar."""
    if timestamp is None:
        timestamp = datetime.now().strftime("%I:%M %p")

    # You'll need to add a 'user-icon.png' to your 'assets/icons/' directory.
    avatar_src = "/assets/icons/user-icon.png" if is_user else "/assets/images/blue_thumb_logo.png"
    message_class = "user-message-row" if is_user else "assistant-message-row"

    avatar = html.Img(src=avatar_src, className="chat-avatar")

    message_bubble = html.Div(
        text,
        className=f"chat-message {'user-message' if is_user else 'assistant-message'}"
    )
    
    if is_user:
        # For the user, the bubble comes before the avatar
        content = [message_bubble, avatar]
    else:
        # For the assistant, the avatar comes first
        content = [avatar, message_bubble]

    # The container for the whole row (avatar and bubble)
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

# Load context once when the app starts
FULL_CONTEXT = load_all_context()

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
        [Output({"type": "chat-messages", "tab": MATCH}, "children"),
         Output({"type": "chat-input", "tab": MATCH}, "value")],
        [Input({"type": "chat-submit", "tab": MATCH}, "n_clicks"),
         Input({"type": "chat-input", "tab": MATCH}, "n_submit")],
        [State({"type": "chat-input", "tab": MATCH}, "value"),
         State({"type": "chat-messages", "tab": MATCH}, "children")],
        prevent_initial_call=True
    )
    def handle_chat_message(n_clicks, n_submit, message, existing_messages):
        """Handle new chat messages and generate responses"""
        if (n_clicks is None and n_submit is None) or not message:
            return existing_messages or [], ""
        
        if existing_messages is None:
            existing_messages = []
        
        # Add user message
        existing_messages.append(format_message(message, is_user=True))
        
        try:
            # Prepare conversation for OpenAI using the pre-loaded full context
            # NOTE: The 'responses' API uses a different input structure
            messages = [
                {"role": "system", "content": f"""You are a helpful stream health expert assistant. 
                Use this context to answer questions: {FULL_CONTEXT}
                Keep responses concise and focused on stream health topics."""},
                {"role": "user", "content": message}
            ]
            
            # Get response from OpenAI with cost-effective settings
            client = openai.OpenAI()
            response = client.chat.completions.create(
                model=CHAT_MODEL,
                messages=messages,
                temperature=TEMPERATURE,
                max_tokens=MAX_TOKENS,
            )
            
            # Add assistant response
            # NOTE: The response object has a different structure
            assistant_message = response.choices[0].message.content
            existing_messages.append(format_message(assistant_message, is_user=False))
            
        except Exception as e:
            error_message = "I apologize, but I'm having trouble responding right now. Please try again."
            existing_messages.append(format_message(error_message, is_user=False))
            print(f"Error in chat response: {e}")
        
        return existing_messages, "" 