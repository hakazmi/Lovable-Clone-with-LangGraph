import os
from openai import OpenAI
from dotenv import load_dotenv
import json

load_dotenv()
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

def parse_json_response(raw_response: str) -> dict:
    """
    Use LLM to parse and fix a potentially malformed JSON response into a clean dictionary.
    Assumes the response contains a file map like {'output': {'pages/index.js': '...', ...}}.
    """
    if not client:
        raise RuntimeError("OPENAI_API_KEY not set in environment")
    
    system_prompt = (
        "You are a JSON parser. Extract and fix the JSON object from the input. "
        "Ensure the output is a valid JSON object with an 'output' key containing the file map "
        "(e.g., {'output': {'pages/index.js': '...', ...}}). "
        "Remove any markdown code blocks, fix single quotes to double quotes, "
        "and ensure it's valid JSON. Output ONLY the cleaned JSON object."
    )
    user_prompt = f"Raw response: {raw_response}"
    
    messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}]
    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=messages,
        max_tokens=4096,  # Increased for larger responses
        temperature=0.0  # Low temperature for deterministic output
    )
    
    cleaned_json_str = response.choices[0].message.content.strip()
    
    # Parse the cleaned string to a dict
    try:
        parsed = json.loads(cleaned_json_str)
        if not isinstance(parsed, dict) or "output" not in parsed:
            print(f"LLM did not return expected structure: {cleaned_json_str}")
            return {"output": {}}
        return parsed
    except json.JSONDecodeError:
        print(f"LLM parsing failed to produce valid JSON: {cleaned_json_str}")
        return {"output": {}}  # Return empty output dict on failure