print("script started")

import os
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()
key = os.getenv("ANTHROPIC_API_KEY")
print("key loaded:", key[:15] + "..." if key else "NONE FOUND")

client = Anthropic()  # reads the key from your .env automatically

response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=200,
    messages=[{"role": "user", "content": "Say hello and tell me one fact about solar flares."}]
)

print(response.content[0].text)