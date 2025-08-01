import streamlit as st
import requests
import json
import pandas as pd
import streamlit.components.v1 as components

API_URL = "https://excel-mock-interviewer.onrender.com"
TOTAL_QUESTIONS = 8

st.set_page_config(page_title="Excel Mock Interviewer", page_icon="🤖")

# 🔊 Voice Output
def speak_js(text):
    escaped = text.replace('"', r'\"')
    components.html(f"""
        <script>
        const msg = new SpeechSynthesisUtterance("{escaped}");
        msg.rate = 1; msg.pitch = 1; msg.lang = 'en-US';
        window.speechSynthesis.speak(msg);
        </script>
    """, height=0)

# 🎤 Voice Input from Browser
def record_with_browser():
    components.html("""
    <script>
    const streamlitSpeechToText = () => {
        var SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        var recognition = new SpeechRecognition();
        recognition.lang = 'en-US';
        recognition.onstart = () => {
            document.getElementById("status").innerText = "🎙️ Listening...";
        };
        recognition.onspeechend = () => {
            recognition.stop();
            document.getElementById("status").innerText = "✅ Done";
        };
        recognition.onresult = (event) => {
            const transcript = event.results[0][0].transcript;
            window.parent.postMessage({type: 'streamlit:setComponentValue', value: transcript}, '*');
        };
        recognition.start();
    };
    </script>
    <div style="margin-bottom:10px;">
        <button onclick="streamlitSpeechToText()">🎙️ Start Speaking</button>
        <p id="status" style="color:green;"></p>
    </div>
    """, height=150)

# Session state setup
if "question" not in st.session_state:
    st.session_state.question = None
    st.session_state.q_index = 0
    st.session_state.history = []
    st.session_state.input_mode = "Text"
    st.session_state.finished = False
    st.session_state.interview_started = False
    st.session_state.interview_initialized = False

# Header
st.markdown("## 🤖 Excel Mock Interviewer")
st.caption("🎙️ Voice-enabled · Powered by Gemini Flash 1.5")

st.markdown("""
<div style="background-color:#1e1e1e;padding:16px 24px;border-radius:8px;margin-bottom:20px;border-left:4px solid #4CAF50">
    <h4 style="color:#FFD700;margin-bottom:6px;">👋 Welcome to Your Excel Mock Interview</h4>
    <p style="color:#ccc;margin:0;">You’ll be asked <b>8 advanced Excel questions</b>.</p>
    <ul style="color:#ccc;margin-top:6px;">
        <li>✅ Instant score & feedback</li>
        <li>🧠 Suggestions to improve</li>
        <li>🎤 Answer using Text or Voice (Browser mic)</li>
    </ul>
</div>
""", unsafe_allow_html=True)

# Start Interview
if not st.session_state.interview_started:
    if st.button("🚀 Start Interview"):
        st.session_state.interview_started = True
        st.rerun()
    st.stop()

# Play welcome voice once
if st.session_state.interview_started and not st.session_state.interview_initialized:
    speak_js("Welcome to your AI-powered Excel Mock Interview. You will be asked 8 questions. After each answer, you will receive a score and tips to improve.")
    st.session_state.interview_initialized = True

# Controls
col1, col2, col3 = st.columns([3, 2, 2])
with col1:
    if st.button("🔁 Start New Interview"):
        try:
            requests.get(f"{API_URL}/reset")
        except:
            st.error("❌ Failed to reset backend.")
        st.session_state.clear()
        st.rerun()
with col2:
    if st.button("✍️ Text Mode"):
        st.session_state.input_mode = "Text"
with col3:
    if st.button("🎙️ Voice Mode"):
        st.session_state.input_mode = "Voice"

st.markdown(f"📥 **Input Mode:** `{st.session_state.input_mode}`")
st.markdown("---")

# Load question
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

# Finished
if st.session_state.finished:
    st.success("✅ Interview Completed!")
    total_score, scores = 0, []
    for i, entry in enumerate(st.session_state.history):
        eval_data = entry["evaluation"]
        if isinstance(eval_data, str):
            try:
                eval_data = json.loads(eval_data)
            except:
                continue
        score = eval_data.get("score", 0)
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
        total_score += score
        scores.append(score)
    st.success(f"🏁 Total Score: {total_score}/{len(scores)*10} | Avg: {total_score/len(scores):.2f}/10")
    df = pd.DataFrame({"Score": scores}, index=[f"Q{i+1}" for i in range(len(scores))])
    st.bar_chart(df)
    st.stop()

# Display current question
st.markdown(f"### 🔢 Question {st.session_state.q_index + 1} of {TOTAL_QUESTIONS}")
st.progress((st.session_state.q_index + 1) / TOTAL_QUESTIONS)
st.info(st.session_state.question)

# Input section
user_answer = ""
if st.session_state.input_mode == "Text":
    user_answer = st.text_area("Your Answer", key=f"text_input_q{st.session_state.q_index}")
else:
    st.markdown("🎤 Speak your answer using browser mic:")
    record_with_browser()
    user_answer = st.text_input("Transcribed Answer", key="voice_input")

# Submit answer
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
        speak_js("Here is your next question.")
    else:
        st.session_state.finished = True

    if eval_result.get("score", 0) >= 7:
        st.balloons()

    st.rerun()
