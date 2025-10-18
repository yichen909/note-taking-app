# import libraries
import os
from openai import OpenAI
from dotenv import load_dotenv
from pathlib import Path

# Load .env if present
load_dotenv()

# Prefer environment variable; fall back to token.txt in repository root
token = os.getenv("GITHUB_TOKEN")
if not token:
    repo_root = Path(__file__).resolve().parent.parent
    token_file = repo_root / 'token.txt'
    if token_file.exists():
        token = token_file.read_text().strip()

if not token:
    raise RuntimeError(
        "GITHUB_TOKEN not found. Set the GITHUB_TOKEN environment variable or add a token.txt file in the project root containing the token."
    )

endpoint = "https://models.github.ai/inference"
model = "openai/gpt-4.1-mini"

# A function to call an LLM model and return the response
def call_llm_model(model, messages, temperature=1.0, top_p=1.0):
    client = OpenAI(base_url=endpoint,api_key=token)
    response = client.chat.completions.create(
        messages=messages,
        temperature=temperature, top_p=top_p, model=model)
    return response.choices[0].message.content

# A function to translate text using the LLM model
def translate(text, target_language):
    prompt=f"Translate the following text to {target_language}:\n\n{text}"
    messages = [{"role": "user", "content": prompt}]
    return call_llm_model(model, messages)

# main function
if __name__ == "__main__":
    sample_text = "Hello, how are you?"
    target_lang = "chinese"
    translated_text = translate(sample_text, target_lang)
    print(f"Original:{sample_text}")
    print(f"Translated:{translated_text}")