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

def format_message(text, is_user=True, timestamp=None, is_typing=False):
    """Format a chat message with appropriate styling and an avatar."""
    if timestamp is None:
        timestamp = datetime.now().strftime("%I:%M %p")

    # You'll need to add a 'user-icon.png' to your 'assets/icons/' directory.
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
            messages = [
                {"role": "system", "content": f"""You are a helpful stream health expert assistant. 
                Use this context to answer questions: {FULL_CONTEXT}
                Keep responses concise and focused on stream health topics."""},
                {"role": "user", "content": message}
            ]
            
            client = openai.OpenAI()
            response = client.chat.completions.create(
                model=CHAT_MODEL,
                messages=messages,
                temperature=TEMPERATURE,
                max_tokens=MAX_TOKENS,
            )
            
            assistant_message = response.choices[0].message.content
            
        except Exception as e:
            assistant_message = "I apologize, but I'm having trouble responding right now. Please try again."
            print(f"Error in chat response: {e}")
        
        # Replace the typing indicator with the actual response
        if existing_messages and len(existing_messages) > 0:
            existing_messages[-1] = format_message(assistant_message, is_user=False)
        
        return existing_messages

    # This clientside callback handles auto-scrolling
    app.clientside_callback(
        """
        function(children) {
            // Give a brief moment for the DOM to update after a new message
            setTimeout(function() {
                try {
                    // Find the container based on its class name.
                    // This assumes only one chat window is active and in the DOM at a time.
                    const element = document.querySelector('.chat-messages-container');
                    if (element) {
                        element.scrollTop = element.scrollHeight;
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