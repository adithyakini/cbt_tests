import streamlit as st
import random
import time
import json
from collections import defaultdict
from openai import OpenAI

# ==================================
# CONFIG
# ==================================

st.set_page_config(page_title="EdgeUp CBT Engine", layout="wide")

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

QUESTION_BANK_SIZE = 60
EXAM_TIME_LIMIT = 900

# ==================================
# PROMPT
# ==================================

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
      "domain":"string",
      "difficulty":"easy | medium | hard"
    }
  ]
}
"""

# ==================================
# QUESTION GENERATION
# ==================================

@st.cache_data
def generate_question_bank(exam_type):

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        response_format={"type": "json_object"},
        temperature=0.6,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"""
Generate {QUESTION_BANK_SIZE} certification questions for {exam_type}.
Include easy, medium, hard questions across domains.
"""
            }
        ]
    )

    data = json.loads(response.choices[0].message.content)

    return data["questions"]

# ==================================
# CREATE EXAM
# ==================================

def create_exam(bank, num_questions):
    return random.sample(bank, num_questions)

# ==================================
# EVALUATION
# ==================================

def evaluate_exam(questions, answers):

    score = 0
    incorrect = []
    domain_stats = defaultdict(lambda: {"correct":0,"total":0})

    for q in questions:

        qid = q["question_id"]
        correct = sorted(q["correct_answers"])
        user = answers.get(qid)

        if not isinstance(user, list):
            user = [user] if user else []

        domain = q["domain"]

        domain_stats[domain]["total"] += 1

        if sorted(user) == correct:
            score += 1
            domain_stats[domain]["correct"] += 1
        else:
            incorrect.append(q)

    return score, incorrect, domain_stats

# ==================================
# AI WEAKNESS ANALYSIS
# ==================================

def analyze_weakness(domain_stats):

    summary = "\n".join(
        [f"{d}: {v['correct']}/{v['total']}" for d,v in domain_stats.items()]
    )

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.3,
        messages=[
            {"role":"system","content":"You are a certification coach."},
            {"role":"user","content":f"""
Analyze exam results and suggest improvement areas.

{summary}
"""}
        ]
    )

    return response.choices[0].message.content

# ==================================
# HEADER
# ==================================

st.title("🎓 EdgeUp")
st.caption("Adaptive CBT Engine | ΛVICΛ 2026")

st.markdown("---")

exam_type = st.selectbox(
    "Exam",
    [
        "AZ-900",
        "AZ-104",
        "FinOps Practitioner",
        "DV360 Programmatic Advertising"
    ]
)

num_questions = st.slider(
    "Questions",
    5,
    25,
    10
)

# ==================================
# LOAD QUESTION BANK
# ==================================

if st.button("Load Question Bank"):

    with st.spinner("Generating questions..."):

        bank = generate_question_bank(exam_type)

        st.session_state.bank = bank

        st.success(f"{len(bank)} questions generated")

# ==================================
# START EXAM
# ==================================

if "bank" in st.session_state:

    if st.button("Start Exam"):

        st.session_state.exam_questions = create_exam(
            st.session_state.bank,
            num_questions
        )

        st.session_state.answers = {}
        st.session_state.flagged = set()
        st.session_state.current_q = 0
        st.session_state.start_time = time.time()
        st.session_state.submitted = False

# ==================================
# EXAM UI
# ==================================

if "exam_questions" in st.session_state and not st.session_state.submitted:

    elapsed = int(time.time() - st.session_state.start_time)
    remaining = max(EXAM_TIME_LIMIT - elapsed, 0)

    st.sidebar.metric("⏱ Time Remaining", f"{remaining}s")

    questions = st.session_state.exam_questions
    q_index = st.session_state.current_q
    q = questions[q_index]

    # =====================
    # Navigator Panel
    # =====================

    st.sidebar.markdown("### Question Navigator")

    cols = st.sidebar.columns(5)

    for i in range(len(questions)):

        label = str(i+1)

        if i in st.session_state.flagged:
            label = f"🚩{label}"

        if cols[i%5].button(label):
            st.session_state.current_q = i
            st.rerun()

    # =====================
    # QUESTION
    # =====================

    st.markdown(f"### Question {q_index+1}")

    st.write(q["question"])

    options = list(q["options"].keys())

    selected = st.radio(
        "Choose one:",
        options,
        format_func=lambda x: f"{x}. {q['options'][x]}",
        index=None,
        key=f"q_{q['question_id']}"
    )

    st.session_state.answers[q["question_id"]] = selected

    # =====================
    # FLAG BUTTON
    # =====================

    if st.button("🚩 Flag Question"):

        st.session_state.flagged.add(q_index)

    # =====================
    # NAV BUTTONS
    # =====================

    col1,col2,col3 = st.columns(3)

    with col1:
        if st.button("Previous") and q_index>0:
            st.session_state.current_q -= 1
            st.rerun()

    with col2:
        if st.button("Next") and q_index < len(questions)-1:
            st.session_state.current_q += 1
            st.rerun()

    with col3:
        if st.button("Review Exam"):
            st.session_state.review = True
            st.rerun()

# ==================================
# REVIEW SCREEN
# ==================================

if st.session_state.get("review"):

    st.subheader("Review Before Submission")

    questions = st.session_state.exam_questions

    for i,q in enumerate(questions):

        answered = q["question_id"] in st.session_state.answers

        flag = "🚩" if i in st.session_state.flagged else ""

        st.write(f"{i+1}. {'Answered' if answered else 'Not answered'} {flag}")

    if st.button("Submit Exam"):
        st.session_state.submitted = True

# ==================================
# RESULTS
# ==================================

if st.session_state.get("submitted"):

    score, incorrect, domain_stats = evaluate_exam(
        st.session_state.exam_questions,
        st.session_state.answers
    )

    total = len(st.session_state.exam_questions)

    st.success(f"Score: {score}/{total}")

    st.markdown("---")

    st.subheader("Domain Performance")

    for domain,stats in domain_stats.items():

        pct = int((stats["correct"]/stats["total"])*100)

        st.write(f"{domain} — {pct}%")

    st.markdown("---")

    if incorrect:

        st.subheader("Review Incorrect Questions")

        for q in incorrect:

            st.markdown("---")

            st.write(q["question"])
            st.write("Correct:", ", ".join(q["correct_answers"]))
            st.write("Explanation:", q["explanation"])

    st.markdown("---")

    st.subheader("AI Study Plan")

    weakness = analyze_weakness(domain_stats)

    st.write(weakness)

    st.balloons()
