from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from gemini import evaluate_answer, model
import json
import ast
import re

app = FastAPI()

# -------------------------------
# Enable CORS for frontend access
# -------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------
# In-memory session store
# -------------------------------
session_questions = {}  # {session_id: {"questions": [...], "index": 0, "history": [...]}}


# -------------------------------
# 🧠 Parse Gemini list output
# -------------------------------
def parse_question_list(raw_text: str) -> list:
    if raw_text.startswith("```python"):
        raw_text = raw_text[len("```python"):].strip()
    if raw_text.endswith("```"):
        raw_text = raw_text[:-3].strip()

    match = re.search(r"=\s*(\[[\s\S]*?\])", raw_text)
    if match:
        list_str = match.group(1)
    else:
        match = re.search(r"(\[[\s\S]*?\])", raw_text)
        if not match:
            raise ValueError("❌ Could not locate a valid Python list in Gemini output.")
        list_str = match.group(1)

    questions = ast.literal_eval(list_str)
    if not isinstance(questions, list) or not all(isinstance(q, str) for q in questions):
        raise ValueError("Parsed output is not a valid list of strings.")
    return questions


# -------------------------------
# GET /question – Get next question
# -------------------------------
@app.get("/question")
def get_question(request: Request):
    session_id = request.client.host or "default_user"

    if session_id not in session_questions:
        prompt = """
You're a senior Excel Interview Agent. Generate a set of 8 advanced-level Excel interview questions.

The questions must test deep proficiency in:
- INDEX-MATCH vs XLOOKUP
- PivotTables and Power Query
- Dynamic named ranges and array formulas
- Data validation, error handling (IFERROR, ISERROR)
- Excel Charts, VBA, Conditional Formatting
- Advanced formulas and data cleaning

Return ONLY a Python list of strings (no variable name, no explanation).
["Question 1...", "Question 2...", "Question 3..."]
"""
        try:
            response = model.generate_content(prompt)
            questions = parse_question_list(response.text.strip())
            print("✅ Questions generated successfully")
        except Exception as e:
            print("❌ Failed to parse Gemini response:", e)
            return {
                "error": "❌ Could not generate questions.",
                "details": str(e)
            }

        session_questions[session_id] = {
            "questions": questions,
            "index": 0,
            "history": []
        }

    qstate = session_questions[session_id]
    if qstate["index"] < len(qstate["questions"]):
        return {"question": qstate["questions"][qstate["index"]]}
    else:
        return {"done": True}


# -------------------------------
# POST /answer – Submit answer
# -------------------------------
@app.post("/answer")
async def submit_answer(request: Request):
    session_id = request.client.host or "default_user"
    data = await request.json()
    user_answer = data.get("answer", "").strip()

    qstate = session_questions.get(session_id)
    if not qstate or qstate["index"] >= len(qstate["questions"]):
        return {"error": "❌ No more questions left."}

    current_question = qstate["questions"][qstate["index"]]

    # Evaluate
    try:
        result_json = evaluate_answer(current_question, user_answer)
        print("🧠 Evaluation raw output:", result_json)
    except Exception as e:
        print("❌ Evaluation failed:", e)
        result_json = {
            "score": 0,
            "feedback": "❌ Gemini API error.",
            "improvement": "Try rephrasing or submitting again later."
        }

    if not isinstance(result_json, dict):
        try:
            result_json = json.loads(result_json)
        except:
            result_json = {
                "score": 0,
                "feedback": "❌ Gemini returned invalid evaluation.",
                "improvement": "Try rephrasing your answer."
            }

    if not all(k in result_json for k in ("score", "feedback", "improvement")):
        result_json = {
            "score": 0,
            "feedback": "❌ Evaluation missing expected fields.",
            "improvement": "Please retry with a more complete answer."
        }

    # Save result
    qstate["history"].append({
        "question": current_question,
        "user_answer": user_answer,
        "evaluation": result_json
    })

    qstate["index"] += 1
    next_question = (
        qstate["questions"][qstate["index"]]
        if qstate["index"] < len(qstate["questions"])
        else None
    )

    return {
        "evaluation": json.dumps(result_json),
        "next_question": next_question
    }


# -------------------------------
# GET /reset – Reset session
# -------------------------------
@app.get("/reset")
def reset_session(request: Request):
    session_id = request.client.host or "default_user"
    if session_id in session_questions:
        del session_questions[session_id]
        print(f"🔁 Session reset for {session_id}")
    return {"status": "reset complete"}