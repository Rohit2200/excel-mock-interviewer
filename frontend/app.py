import streamlit as st
import requests
import json
import speech_recognition as sr
import sounddevice as sd
from scipy.io.wavfile import write
import pandas as pd
import streamlit.components.v1 as components

API_URL = "http://127.0.0.1:8000"
TOTAL_QUESTIONS = 8
SAMPLE_RATE = 44100

st.set_page_config(page_title="Excel Mock Interviewer", page_icon="🤖")

# ----------------------------- #
# 🔊 Voice Assistant via JS
# ----------------------------- #
def speak_js(text):
    escaped = text.replace('"', r'\"')
    components.html(f"""
        <script>
        const msg = new SpeechSynthesisUtterance("{escaped}");
        msg.rate = 1; msg.pitch = 1; msg.lang = 'en-US';
        window.speechSynthesis.speak(msg);
        </script>
    """, height=0)

# ----------------------------- #
# 🧠 Session Initialization
# ----------------------------- #
if "question" not in st.session_state:
    st.session_state.question = None
    st.session_state.q_index = 0
    st.session_state.history = []
    st.session_state.input_mode = "Text"
    st.session_state.audio_transcript = ""
    st.session_state.audio_data = None
    st.session_state.recorded_file = None
    st.session_state.finished = False
    st.session_state.interview_started = False
    st.session_state.voice_intro_played = False

# ----------------------------- #
# 🧠 Intro & Start Logic
# ----------------------------- #
st.markdown("## 🤖 Excel Mock Interviewer")
st.caption("🎙️ Powered by Gemini Flash 1.5 · Text or Voice supported")

st.markdown("""
<div style="background-color:#1e1e1e;padding:16px 24px;border-radius:8px;margin-bottom:20px;border-left:4px solid #4CAF50">
    <h4 style="color:#FFD700;margin-bottom:6px;">👋 Welcome to Your Excel Mock Interview</h4>
    <p style="color:#ccc;margin:0;">You’ll be asked <b>8 advanced Excel questions</b>.</p>
    <ul style="color:#ccc;margin-top:6px;">
        <li>✅ Instant score & feedback</li>
        <li>🧠 Suggestions to improve</li>
        <li>🎤 Answer using Text or Voice</li>
        <li>⚠️ In Voice Mode: Transcribe before Submit</li>
    </ul>
</div>
""", unsafe_allow_html=True)

# Step 1: Show Start Interview button
if not st.session_state.interview_started:
    if st.button("🚀 Start Interview"):
        st.session_state.interview_started = True
        st.session_state.interview_initialized = False  # NEW
        st.rerun()
    st.stop()

# 🗣️ After rerun, play intro only once
if st.session_state.interview_started and not st.session_state.get("interview_initialized", False):
    speak_js("Welcome to your AI-powered Excel Mock Interview. You will be asked 8 questions. After each answer, you will receive a score and tips to improve.")
    st.session_state.interview_initialized = True


# Step 2: After voice plays, proceed with interview
if st.session_state.voice_intro_played and not st.session_state.interview_started:
    st.session_state.interview_started = True
    st.rerun()

# Step 3: Wait until started
if not st.session_state.interview_started:
    st.stop()

# ----------------------------- #
# 🔁 Control Panel
# ----------------------------- #
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

# ----------------------------- #
# 🧠 Load Question
# ----------------------------- #
if st.session_state.question is None and not st.session_state.finished:
    try:
        res = requests.get(f"{API_URL}/question")
        data = res.json()
        if "question" in data:
            st.session_state.question = data["question"]
        elif data.get("done"):
            st.session_state.finished = True
        elif "error" in data:
            st.error(f"❌ Gemini API failed: {data.get('error')}")
            st.stop()
        else:
            st.error("❌ Unexpected error loading question.")
            st.stop()
    except Exception as e:
        st.error(f"❌ Backend unreachable: {e}")
        st.stop()

# ----------------------------- #
# ✅ Interview Complete
# ----------------------------- #
if st.session_state.finished:
    st.success("✅ Interview Completed!")
    st.subheader("📊 Final Score Summary")

    total_score, scores = 0, []
    for i, entry in enumerate(st.session_state.history):
        eval_data = entry["evaluation"]
        if isinstance(eval_data, str):
            try:
                eval_data = json.loads(eval_data)
            except:
                st.warning(f"⚠️ Skipped Q{i+1} due to format issue.")
                continue

        score = eval_data.get("score", 0)
        emoji = "✅" if score >= 7 else "⚠️" if score >= 4 else "❌"
        st.markdown(f"""
        <div style="background:#f9f9fa;border:1px solid #ddd;padding:15px;border-radius:10px;margin-bottom:10px;color:#000;">
        <h5>{emoji} Q{i+1}</h5>
        <b>Question:</b> {entry['question']}<br><br>
        <b>Your Answer:</b> {entry['answer']}<br><br>
        <b>Score:</b> {score}/10<br>
        <b>Feedback:</b> {eval_data.get("feedback", "N/A")}<br>
        <b>Improvement:</b> {eval_data.get("improvement", "N/A")}
        </div>
        """, unsafe_allow_html=True)

        total_score += score
        scores.append(score)

    if scores:
        avg = total_score / len(scores)
        st.success(f"🏁 Total Score: {total_score}/{len(scores)*10} | Avg: {avg:.2f}/10")
        df = pd.DataFrame({"Score": scores}, index=[f"Q{i+1}" for i in range(len(scores))])
        st.bar_chart(df)
    else:
        st.warning("⚠️ No answers recorded.")

    st.stop()

# ----------------------------- #
# ❓ Current Question
# ----------------------------- #
st.markdown(f"### 🔢 Question {st.session_state.q_index + 1} of {TOTAL_QUESTIONS}")
st.progress(min((st.session_state.q_index + 1) / TOTAL_QUESTIONS, 1.0))
st.markdown(f"""
<div style="background:#f0f2f6;padding:20px;border-radius:10px;color:#000;font-weight:500;">
{st.session_state.question}
</div>
""", unsafe_allow_html=True)

# ----------------------------- #
# 🧾 Answer Input Section
# ----------------------------- #
user_answer = ""

if st.session_state.input_mode == "Text":
    user_answer = st.text_area("Your Answer", key=f"text_input_q{st.session_state.q_index}", value="")

else:
    st.markdown("🎤 Record your voice and transcribe it.")
    audio_filename = f"voice_q{st.session_state.q_index + 1}.wav"

    if st.button("🎙️ Start Recording"):
        st.session_state.audio_transcript = ""
        try:
            st.info("🔴 Recording... Speak now.")
            recording = sd.rec(int(60 * SAMPLE_RATE), samplerate=SAMPLE_RATE, channels=1, dtype='int16')
            sd.wait()
            write(audio_filename, SAMPLE_RATE, recording)
            st.session_state.recorded_file = audio_filename
            st.success("✅ Recording saved.")
        except Exception as e:
            st.error(f"❌ Recording failed: {e}")

    if st.session_state.recorded_file:
        st.audio(st.session_state.recorded_file, format="audio/wav")
        if st.button("⏹️ Transcribe"):
            try:
                recognizer = sr.Recognizer()
                with sr.AudioFile(st.session_state.recorded_file) as source:
                    audio = recognizer.record(source)
                    transcript = recognizer.recognize_google(audio)
                    st.session_state.audio_transcript = transcript
                    st.success(f"🗣️ Transcribed: {transcript}")
            except sr.UnknownValueError:
                st.error("😕 Could not understand.")
            except sr.RequestError:
                st.error("⚠️ Speech recognition service error.")

        user_answer = st.session_state.audio_transcript

# ----------------------------- #
# ✅ Submit Button
# ----------------------------- #
st.markdown("<br>", unsafe_allow_html=True)
center = st.columns([1, 2, 1])[1]
with center:
    if st.button("✅ Submit Answer"):
        if not user_answer.strip():
            st.warning("⚠️ Please provide an answer.")
            st.stop()

        try:
            res = requests.post(f"{API_URL}/answer", json={"answer": user_answer})
            data = res.json()
            raw_eval = data.get("evaluation", "{}")
            eval_result = json.loads(raw_eval) if isinstance(raw_eval, str) else raw_eval
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
        st.session_state.audio_transcript = ""
        st.session_state.recorded_file = None

        if data.get("next_question"):
            st.session_state.question = data["next_question"]
            speak_js("Here is your next question.")
        else:
            st.session_state.finished = True

        if eval_result.get("score", 0) >= 7:
            st.balloons()

        st.rerun()
