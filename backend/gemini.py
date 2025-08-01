# backend/gemini.py

import os
from dotenv import load_dotenv
import google.generativeai as genai
import re
import json

# Load Gemini API Key
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Configure Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

def evaluate_answer(question: str, user_answer: str) -> str:
    prompt = f"""
You are an AI Excel Interviewer.

Evaluate the following answer to this interview question:

Question: "{question}"
Answer: "{user_answer}"

Return ONLY a JSON object in this exact format:

{{
  "score": <number from 0 to 10>,
  "feedback": "<1-2 line explanation>",
  "improvement": "<short suggestion>"
}}

DO NOT add any commentary before or after the JSON. Just return the JSON.
"""

    # Get Gemini response
    response = model.generate_content(prompt).text.strip()

    # Extract just the JSON from the response using regex
    match = re.search(r'\{.*\}', response, re.DOTALL)

    if match:
        try:
            # Validate it is real JSON
            parsed = json.loads(match.group())
            return json.dumps(parsed)
        except json.JSONDecodeError:
            # Invalid JSON - return fallback
            return json.dumps({
                "score": 0,
                "feedback": "⚠️ Could not parse Gemini response.",
                "improvement": "Please try rephrasing the answer."
            })
    else:
        # Gemini didn’t return JSON
        return json.dumps({
            "score": 0,
            "feedback": "⚠️ Gemini returned invalid output.",
            "improvement": "Ensure strict JSON format in prompt."
        })
