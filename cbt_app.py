import streamlit as st
import random
import time
import json
from openai import OpenAI

# ==========================
# CONFIG
# ==========================

st.set_page_config(page_title="AI CBT Engine", layout="wide")

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

QUESTION_BANK_SIZE = 50


# ==========================
# PROMPTS
# ==========================

SYSTEM_PROMPT = """
You are a certification exam generator.

Return ONLY valid JSON.

{
  "questions":[
    {
      "question_id": number,
      "question_type":"single",
      "question":"string",
      "options":{"A":"", "B":"", "C":"", "D":""},
      "correct_answers":["A"],
      "explanation":"string",
      "domain":"string"
    }
  ]
}
"""


# ==========================
# GENERATE QUESTION BANK
# ==========================

@st.cache_data(show_spinner=True)
def generate_question_bank(exam_type, difficulty):

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        response_format={"type": "json_object"},
        temperature=0.7,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content":
                f"Generate {QUESTION_BANK_SIZE} {difficulty} certification exam questions for {exam_type}"}
        ]
    )

    data = json.loads(response.choices[0].message.content)

    return data["questions"]


# ==========================
# CREATE EXAM FROM BANK
# ==========================

def create_exam(bank, num_questions):
    return random.sample(bank, num_questions)


# ==========================
# EVALUATION
# ==========================

def evaluate_exam(questions, answers):

    score = 0
    incorrect = []

    for q in questions:

        qid = q["question_id"]
        correct = sorted(q["correct_answers"])
        user = answers.get(qid)

        if not isinstance(user, list):
            user = [user] if user else []

        if sorted(user) == correct:
            score += 1
        else:
            incorrect.append(q)

    return score, incorrect


# ==========================
# UI
# ==========================

st.title("🧠 MindKraft — AI-powered certification mastery")
st.footer("Λ Ｖ I Ｃ Λ 2026")

exam_type = st.selectbox(
    "Exam",
    ["AZ-900", "AZ-104", "FinOps Practitioner","DV360 programmatic advertising interview questions"]
)

difficulty = st.selectbox(
    "Difficulty",
    ["Easy", "Medium", "Hard"]
)

num_questions = st.slider(
    "Questions",
    5,
    20,
    10
)

# ==========================
# GENERATE QUESTION BANK
# ==========================

if st.button("Load Question Bank"):

    with st.spinner("Generating question bank..."):

        bank = generate_question_bank(exam_type, difficulty)

        st.session_state.bank = bank

        st.success(f"{len(bank)} questions generated and cached")


# ==========================
# START EXAM
# ==========================

if "bank" in st.session_state:

    if st.button("Start Exam"):

        exam_questions = create_exam(
            st.session_state.bank,
            num_questions
        )

        st.session_state.exam_questions = exam_questions
        st.session_state.answers = {}
        st.session_state.start_time = time.time()
        st.session_state.submitted = False


# ==========================
# EXAM UI
# ==========================

if "exam_questions" in st.session_state:

    elapsed = int(time.time() - st.session_state.start_time)

    st.sidebar.write(f"⏱ Time: {elapsed}s")

    for q in st.session_state.exam_questions:

        st.markdown("---")
        st.write(f"### {q['question']}")

        options = list(q["options"].keys())

        if q["question_type"] == "single":

            selected = st.radio(
                "Choose one:",
                options,
                format_func=lambda x: f"{x}. {q['options'][x]}",
                key=q["question_id"]
            )

        else:

            selected = st.multiselect(
                "Choose two:",
                options,
                format_func=lambda x: f"{x}. {q['options'][x]}",
                key=q["question_id"]
            )

        st.session_state.answers[q["question_id"]] = selected

    if st.button("Submit Exam"):
        st.session_state.submitted = True


# ==========================
# RESULTS
# ==========================

if st.session_state.get("submitted"):

    score, incorrect = evaluate_exam(
        st.session_state.exam_questions,
        st.session_state.answers
    )

    total = len(st.session_state.exam_questions)

    st.success(f"Score: {score}/{total}")

    if incorrect:

        st.subheader("Review")

        for q in incorrect:

            st.markdown("---")
            st.write(q["question"])
            st.write("Correct:", q["correct_answers"])
            st.write("Explanation:", q["explanation"])

    else:
        st.balloons()




