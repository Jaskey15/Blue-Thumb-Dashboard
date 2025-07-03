"""
Simple OpenAI test with cost-effective settings
"""
import os
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Cost-effective model configuration
CHAT_MODEL = "gpt-3.5-turbo-0125"  # Newest, most efficient 3.5 version
MAX_TOKENS = 10  # Keep test response very short
TEMPERATURE = 0.7

def main():
    # Print first 7 chars of key for verification
    key = os.getenv('OPENAI_API_KEY')
    print(f"\nAPI Key starts with: {key[:7] if key else 'Not found!'}")
    
    try:
        # Create client
        client = OpenAI()
        
        # Simple test request with cost-effective settings
        response = client.chat.completions.create(
            model=CHAT_MODEL,
            messages=[{"role": "user", "content": "Say hello!"}],
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS,
            presence_penalty=0,
            frequency_penalty=0
        )
        
        print("\nSuccess! Response:", response.choices[0].message.content)
        print("\nUsage stats:", response.usage)
        
    except Exception as e:
        print(f"\nError details: {str(e)}")

if __name__ == "__main__":
    main()