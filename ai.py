import os
import re
import requests
from dotenv import load_dotenv

load_dotenv()

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")


def mask_sensitive(text):
    """Hide emails and phone numbers before sending text to an external AI service."""
    text = re.sub(r"[\w.+-]+@[\w-]+\.[\w.-]+", "[EMAIL]", text)
    text = re.sub(r"(?<!\d)\+?\d[\d\s-]{8,}\d(?!\d)", "[PHONE]", text)
    return text


def ask_ai(system_prompt, user_prompt):
    """One place that talks to the AI provider. Returns the reply text (JSON)."""
    key = os.getenv("GROQ_API_KEY")
    if not key:
        raise RuntimeError("GROQ_API_KEY is not set")
    resp = requests.post(
        GROQ_URL,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={
            "model": MODEL,
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        },
        timeout=20,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"Groq error {resp.status_code}: {resp.text[:300]}")
    return resp.json()["choices"][0]["message"]["content"]

def list_models():
    key = os.getenv("GROQ_API_KEY")
    r = requests.get("https://api.groq.com/openai/v1/models",
                     headers={"Authorization": f"Bearer {key}"}, timeout=20)
    if r.status_code != 200:
        return f"Error {r.status_code}: {r.text[:300]}"
    return [m["id"] for m in r.json()["data"]]


if __name__ == "__main__":
    try:
        print(ask_ai("You reply only with JSON.",
                     'Reply with this JSON: {"ok": true, "message": "hello from Groq"}'))
    except Exception as e:
        print("AI test failed:", e)