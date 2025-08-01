import streamlit as st
import requests
import json
import pandas as pd

API_URL = "http://127.0.0.1:8000"
TOTAL_QUESTIONS = 8

st.set_page_config(page_title="Excel Mock Interviewer", page_icon="🤖")

# --------------------
# Session State Init
# --------------------
if "question" not in st.session_state:
    st.session_state.question = None
    st.session_state.q_index = 0
    st.session_state.history = []
    st.session_state.finished = False
    st.session_state.interview_started = False
    st.session_state.interview_initialized = False

# --------------------
# Header
# --------------------
st.markdown("## 🤖 Excel Mock Interviewer")
st.caption("✍️ Text-based · Powered by Gemini Flash 1.5")

st.markdown("""
<div style="background-color:#1e1e1e;padding:16px 24px;border-radius:8px;margin-bottom:20px;border-left:4px solid #4CAF50">
    <h4 style="color:#FFD700;margin-bottom:6px;">👋 Welcome to Your Excel Mock Interview</h4>
    <p style="color:#ccc;margin:0;">You’ll be asked <b>8 advanced Excel questions</b>.</p>
    <ul style="color:#ccc;margin-top:6px;">
        <li>✅ Instant score & feedback</li>
        <li>🧠 Suggestions to improve</li>
        <li>✍️ Answer by typing your response</li>
    </ul>
</div>
""", unsafe_allow_html=True)

# --------------------
# Start Interview
# --------------------
if not st.session_state.interview_started:
    if st.button("🚀 Start Interview"):
        st.session_state.interview_started = True
        st.rerun()
    st.stop()

if st.session_state.interview_started and not st.session_state.interview_initialized:
    st.info("Welcome to your AI-powered Excel Mock Interview. You will be asked 8 questions. After each answer, you will receive a score and tips to improve.")
    st.session_state.interview_initialized = True

# --------------------
# Controls
# --------------------
col1, col2 = st.columns([4, 2])
with col1:
    if st.button("🔁 Start New Interview"):
        try:
            requests.get(f"{API_URL}/reset")
        except:
            st.error("❌ Failed to reset backend.")
        st.session_state.clear()
        st.rerun()
with col2:
    st.markdown("✍️ Text mode enabled", unsafe_allow_html=True)

st.markdown("---")

# --------------------
# Load Question
# --------------------
if st.session_state.question is None and not st.session_state.finished:
    try:
        res = requests.get(f"{API_URL}/question")
        data = res.json()
        if "question" in data:
            st.session_state.question = data["question"]
        elif data.get("done"):
            st.session_state.finished = True
        else:
            st.error("❌ Failed to fetch question.")
            st.stop()
    except Exception as e:
        st.error(f"❌ Backend unreachable: {e}")
        st.stop()

# --------------------
# Finished
# --------------------
if st.session_state.finished:
    st.success("✅ Interview Completed!")
    total_score = 0
    scores = []
    for i, entry in enumerate(st.session_state.history):
        eval_data = entry["evaluation"]
        if isinstance(eval_data, str):
            try:
                eval_data = json.loads(eval_data)
            except:
                continue
        score = eval_data.get("score", 0)
        total_score += score
        scores.append(score)

        st.markdown(f"""
        <div style="background:#fff;border:1px solid #ddd;padding:15px;border-radius:10px;margin-bottom:10px;color:#000;">
        <h5>Q{i+1}</h5>
        <b>Question:</b> {entry['question']}<br><br>
        <b>Your Answer:</b> {entry['answer']}<br><br>
        <b>Score:</b> {score}/10<br>
        <b>Feedback:</b> {eval_data.get("feedback", "N/A")}<br>
        <b>Improvement:</b> {eval_data.get("improvement", "N/A")}
        </div>
        """, unsafe_allow_html=True)

    st.success(f"🏁 Total Score: {total_score}/{len(scores)*10} | Avg: {total_score/len(scores):.2f}/10")
    st.bar_chart(pd.DataFrame({"Score": scores}, index=[f"Q{i+1}" for i in range(len(scores))]))
    st.stop()

# --------------------
# Show Question
# --------------------
st.markdown(f"### 🔢 Question {st.session_state.q_index + 1} of {TOTAL_QUESTIONS}")
st.progress((st.session_state.q_index + 1) / TOTAL_QUESTIONS)
st.info(st.session_state.question)

# --------------------
# Input Section
# --------------------
user_answer = st.text_area("✍️ Type your Answer below", key=f"text_input_q{st.session_state.q_index}")

# --------------------
# Submit
# --------------------
if st.button("✅ Submit Answer"):
    if not user_answer.strip():
        st.warning("⚠️ Please provide an answer.")
        st.stop()

    try:
        res = requests.post(f"{API_URL}/answer", json={"answer": user_answer})
        data = res.json()
        eval_raw = data.get("evaluation", "{}")
        eval_result = json.loads(eval_raw) if isinstance(eval_raw, str) else eval_raw
    except Exception as e:
        st.error(f"❌ Failed to evaluate: {e}")
        st.stop()

    st.toast("✅ Answer submitted!", icon="📨")
    st.session_state.history.append({
        "question": st.session_state.question,
        "answer": user_answer,
        "evaluation": eval_result
    })
    st.session_state.q_index += 1

    if data.get("next_question"):
        st.session_state.question = data["next_question"]
    else:
        st.session_state.finished = True

    if eval_result.get("score", 0) >= 7:
        st.balloons()

    st.rerun()
