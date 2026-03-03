import streamlit as st
import time
import os
import json
from dotenv import load_dotenv
from openai import OpenAI

# ==========================
# CONFIG
# ==========================

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

st.set_page_config(page_title="AI CBT Engine", layout="wide")

# ==========================
# PROMPTS
# ==========================

SYSTEM_PROMPT = """
You are an expert certification exam generator.

Return ONLY valid JSON in this structure:

{
  "exam": "string",
  "questions": [
    {
      "question_id": number,
      "question_type": "single" or "multiple",
      "question": "string",
      "options": {
        "A": "string",
        "B": "string",
        "C": "string",
        "D": "string"
      },
      "correct_answers": ["A"],
      "explanation": "string",
      "domain": "string"
    }
  ]
}

Rules:
- Certification-level difficulty.
- Multiple type must contain exactly 2 correct answers.
- Avoid obvious answers.
- Do not include extra text.
"""

COACH_PROMPT = """
You are a certification mentor and cognitive learning coach.

Analyze the user's incorrect answers and:

1. Identify weak knowledge domains
2. Identify thinking mistakes (conceptual gap, misreading, confusion)
3. Provide improvement strategy
4. Suggest 3 targeted practice areas
5. Provide short motivational guidance

Be structured and professional.
"""

# ==========================
# FUNCTIONS
# ==========================

def generate_exam(exam_type, difficulty, num_questions):
    try:
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            response_format={"type": "json_object"},
            temperature=0.7,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content":
                    f"Generate {num_questions} {difficulty} difficulty questions for {exam_type}"
                }
            ]
        )

        return json.loads(response.choices[0].message.content)

    except Exception as e:
        st.error(f"Error generating exam: {e}")
        return None


def evaluate_exam(exam_data, user_answers):
    score = 0
    incorrect_questions = []

    for q in exam_data["questions"]:
        qid = q["question_id"]
        correct = sorted(q["correct_answers"])
        user = user_answers.get(qid)

        if not isinstance(user, list):
            user = [user] if user else []

        if sorted(user) == correct:
            score += 1
        else:
            incorrect_questions.append({
                "question": q["question"],
                "user_answer": user,
                "correct_answer": correct,
                "explanation": q["explanation"],
                "domain": q["domain"]
            })

    return score, incorrect_questions


def generate_learning_feedback(incorrect_questions):
    try:
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            temperature=0.4,
            messages=[
                {"role": "system", "content": COACH_PROMPT},
                {"role": "user", "content":
                    f"Here are the incorrect responses:\n{json.dumps(incorrect_questions, indent=2)}"
                }
            ]
        )

        return response.choices[0].message.content

    except Exception as e:
        return f"Error generating learning feedback: {e}"


# ==========================
# UI
# ==========================

st.title("🧠 AI Certification CBT Platform")

exam_type = st.selectbox(
    "Select Exam",
    ["FinOps Practitioner", "AZ-900", "AZ-104"]
)

difficulty = st.selectbox("Difficulty", ["Easy", "Medium", "Hard"])
num_questions = st.slider("Number of Questions", 5, 30, 10)

# ==========================
# START EXAM
# ==========================

if st.button("Start Exam"):

    exam_data = generate_exam(exam_type, difficulty, num_questions)

    if exam_data:
        st.session_state.exam_data = exam_data
        st.session_state.start_time = time.time()
        st.session_state.answers = {}
        st.session_state.submitted = False

# ==========================
# RENDER EXAM
# ==========================

if "exam_data" in st.session_state:

    elapsed = int(time.time() - st.session_state.start_time)
    st.sidebar.title("Exam Info")
    st.sidebar.write(f"⏱ Time Elapsed: {elapsed} sec")

    st.sidebar.title("Question Navigator")
    for q in st.session_state.exam_data["questions"]:
        st.sidebar.write(f"Q{q['question_id']}")

    for q in st.session_state.exam_data["questions"]:

        st.markdown(f"---")
        st.markdown(f"### Q{q['question_id']}: {q['question']}")

        if q["question_type"] == "single":
            selected = st.radio(
                "Select one answer:",
                options=list(q["options"].keys()),
                format_func=lambda x: f"{x}. {q['options'][x]}",
                key=f"q_{q['question_id']}"
            )
        else:
            selected = st.multiselect(
                "Select TWO answers:",
                options=list(q["options"].keys()),
                format_func=lambda x: f"{x}. {q['options'][x]}",
                key=f"q_{q['question_id']}"
            )

        st.session_state.answers[q["question_id"]] = selected

    if st.button("Submit Exam"):
        st.session_state.submitted = True

# ==========================
# RESULTS + LEARNING COACH
# ==========================

if st.session_state.get("submitted"):

    score, incorrect = evaluate_exam(
        st.session_state.exam_data,
        st.session_state.answers
    )

    total = len(st.session_state.exam_data["questions"])

    st.markdown("---")
    st.subheader("📊 Results")
    st.success(f"Final Score: {score}/{total}")

    if incorrect:
        st.markdown("---")
        st.subheader("🧑‍🏫 Personalized Learning Coach")

        feedback = generate_learning_feedback(incorrect)
        st.markdown(feedback)

    else:
        st.balloons()
        st.success("Perfect score! You're exam ready 🚀")
