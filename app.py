from openai import OpenAI
import os
from pathlib import Path

# Load local environment variables from .env.local if present
env_path = Path(__file__).resolve().parent / ".env.local"
if env_path.exists():
    with env_path.open("r", encoding="utf-8") as env_file:
        for line in env_file:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            os.environ.setdefault(key, value)

api_key = os.environ.get("OPENROUTER_API_KEY")
if not api_key:
    raise RuntimeError("OPENROUTER_API_KEY is not set in the environment or .env.local file.")

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=api_key,
    default_headers={
        "HTTP-Referer": "https://twoj-projekt.local",
        "X-Title": "Magisterka benchmark"
    }
)

response = client.chat.completions.create(
    model="openai/gpt-4o-mini",
    messages=[
        {"role": "user", "content": "Napisz funkcję sprawdzającą palindrom w Pythonie."}
    ],
    temperature=0
)

print(response.choices[0].message.content)
print(response.usage)