"""
Callbacks for the chatbot functionality
"""

from dash import Input, Output, State, callback, html
import dash_bootstrap_components as dbc
from datetime import datetime
import openai
import os
import json

# Cost-effective model configuration
CHAT_MODEL = "gpt-3.5-turbo-0125"  # Newest, most efficient 3.5 version
MAX_TOKENS = 150  # Limit response length
TEMPERATURE = 0.7  # Balance between creativity and consistency

def format_message(text, is_user=True, timestamp=None):
    """Format a chat message with appropriate styling"""
    if timestamp is None:
        timestamp = datetime.now().strftime("%I:%M %p")
        
    return html.Div([
        html.Div(
            text,
            className=f"chat-message {'user-message' if is_user else 'assistant-message'}"
        ),
        html.Div(
            timestamp,
            className="chat-timestamp"
        )
    ])

def load_tab_context(tab_name):
    """Load relevant context based on the current tab"""
    context_map = {
        "chemical": "text/chemical/chemical_intro.md",
        # Add other tab contexts as needed
    }
    
    if tab_name in context_map:
        try:
            with open(context_map[tab_name], 'r') as f:
                return f.read()
        except Exception as e:
            print(f"Error loading context for {tab_name}: {e}")
            return ""
    return ""

def register_chatbot_callbacks(app):
    @app.callback(
        Output({"type": "chat-collapse", "tab": "chemical"}, "is_open"),
        [Input({"type": "chat-toggle", "tab": "chemical"}, "n_clicks"),
         Input({"type": "chat-close", "tab": "chemical"}, "n_clicks")],
        [State({"type": "chat-collapse", "tab": "chemical"}, "is_open")],
        prevent_initial_call=True
    )
    def toggle_chat_collapse(toggle_clicks, close_clicks, is_open):
        """Toggle the chat panel open/closed"""
        if toggle_clicks is None and close_clicks is None:
            return is_open
        return not is_open

    @app.callback(
        [Output({"type": "chat-messages", "tab": "chemical"}, "children"),
         Output({"type": "chat-input", "tab": "chemical"}, "value")],
        [Input({"type": "chat-submit", "tab": "chemical"}, "n_clicks")],
        [State({"type": "chat-input", "tab": "chemical"}, "value"),
         State({"type": "chat-messages", "tab": "chemical"}, "children")],
        prevent_initial_call=True
    )
    def handle_chat_message(n_clicks, message, existing_messages):
        """Handle new chat messages and generate responses"""
        if n_clicks is None or not message:
            return existing_messages or [], ""
        
        if existing_messages is None:
            existing_messages = []
        
        # Add user message
        existing_messages.append(format_message(message, is_user=True))
        
        try:
            # Load relevant context
            context = load_tab_context("chemical")
            
            # Prepare conversation for OpenAI
            messages = [
                {"role": "system", "content": f"""You are a helpful stream health expert assistant. 
                Use this context to answer questions: {context}
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
                presence_penalty=0,  # Reduce token usage
                frequency_penalty=0   # Reduce token usage
            )
            
            # Add assistant response
            assistant_message = response.choices[0].message.content
            existing_messages.append(format_message(assistant_message, is_user=False))
            
        except Exception as e:
            error_message = "I apologize, but I'm having trouble responding right now. Please try again."
            existing_messages.append(format_message(error_message, is_user=False))
            print(f"Error in chat response: {e}")
        
        return existing_messages, "" 