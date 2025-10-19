import os
from datetime import datetime
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

system_prompt = '''
today's date and time: {current_datetime}
Extract the user's notes into the following structured fields:
1. Title: A concise title of the notes less than 5 words
2. Notes: The notes based on user input written in full sentences.
3. Tags (A list): At most 3 Keywords or tags that categorize the content of the notes.
Output in JSON format without ```json. Output title and notes in the language: {lang}.
4. Event Date
5. Event Time
Example:
Input: "Badminton tmr 5pm @polyu".
Output:
{{
 "Title": "Badminton at PolyU",
 "Notes": "Remember to play badminton at 5pm tomorrow at PolyU.",
 "Tags": ["badminton", "sports"]
 "Event Date": "2024-06-05",
 "Event Time": "17:00"
}}
'''

# a function to extract structured notes using LLM model
def extract_structured_notes(user_input, lang="english"):
    current_datetime = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    messages = [
        {
            "role": "system",
            "content": system_prompt.format(
                lang=lang,
                current_datetime=current_datetime,
            ),
        },
        {"role": "user", "content": user_input}
    ]
    response = call_llm_model(model, messages)
    return response

# main function
if __name__ == "__main__":
    # test the extract notes feature
    sample_text = "Badminton tmr 5pm @polyu"
    print("Extracted Structured Notes:")
    print(extract_structured_notes(sample_text, lang="english"))
