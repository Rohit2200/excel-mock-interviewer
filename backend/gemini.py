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

    # Try to get Gemini response
    try:
        response = model.generate_content(prompt).text.strip()
        print("✅ Gemini raw response:", response)
    except Exception as e:
        error_msg = str(e)
        print("❌ Gemini API error:", error_msg)

        # Detect quota or rate-limit issues
        if "quota" in error_msg.lower() or "limit" in error_msg.lower() or "429" in error_msg:
            print("🚫 Gemini API quota/rate limit likely exceeded.")
        else:
            print("⚠️ Unexpected Gemini API error.")

        return json.dumps({
            "score": 0,
            "feedback": "❌ Gemini API request failed.",
            "improvement": "Try again later. Possibly exceeded daily quota."
        })

    # Extract JSON from response
    match = re.search(r'\{.*\}', response, re.DOTALL)
    if match:
        try:
            parsed = json.loads(match.group())
            return json.dumps(parsed)
        except json.JSONDecodeError:
            return json.dumps({
                "score": 0,
                "feedback": "⚠️ Could not parse Gemini response.",
                "improvement": "Please try rephrasing the answer."
            })
    else:
        return json.dumps({
            "score": 0,
            "feedback": "⚠️ Gemini returned invalid output.",
            "improvement": "Ensure strict JSON format in prompt."
        })
