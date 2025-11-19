import os
from dotenv import load_dotenv
from anthropic import Anthropic

# Load environment variables
load_dotenv()

# Initialize client
api_key = os.getenv('ANTHROPIC_API_KEY')
if not api_key:
    print("❌ ERROR: ANTHROPIC_API_KEY not found in .env file")
    exit(1)

client = Anthropic(api_key=api_key)

# Test API call
try:
    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=100,
        messages=[
            {"role": "user", "content": "Say 'API test successful!' if you can read this."}
        ]
    )
    print("✅ API Connection Successful!")
    print(f"Response: {message.content[0].text}")
except Exception as e:
    print(f"❌ API Connection Failed: {e}")
