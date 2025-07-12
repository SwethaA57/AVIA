# Streamlit Frontend
import streamlit as st
import requests

BASE_URL = "http://127.0.0.1:5000"

def login_page():
    st.title("AIVA-The AI Classroom Assistant")
    role = st.selectbox("Select Role", ["Student", "Teacher"])
    action = st.radio("Action", ["Login", "Register"])

    with st.form(key='auth_form'):
        name = st.text_input("Name") if action == "Register" else ""
        institution = st.text_input("Institution") if action == "Register" else ""
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        student_class = st.text_input("Class") if role == "Student" and action == "Register" else ""
        submit = st.form_submit_button("Submit")

        if submit:
            payload = {
                "name": name,
                "institution": institution,
                "email": email,
                "password": password
            }
            if role == "Student":
                payload["student_class"] = student_class

            if action == "Register":
                endpoint = f"/register_{role.lower()}"
                res = requests.post(BASE_URL + endpoint, json=payload)
                if res.status_code == 201:
                    st.success("Registered successfully! Please log in.")
                else:
                    st.error(res.json().get("message", "Registration failed."))
            else:
                endpoint = f"/login_{role.lower()}"
                res = requests.post(BASE_URL + endpoint, json=payload)
                if res.status_code == 200:
                    data = res.json()
                    st.session_state['role'] = role
                    st.session_state['logged_in'] = True
                    st.session_state['name'] = data["name"]
                    st.session_state['user_id'] = data["id"]

                    # Set student_id or teacher_id in session
                    if role == "Student":
                        st.session_state['student_id'] = data["id"]
                    elif role == "Teacher":
                        st.session_state['teacher_id'] = data["id"]

                    st.success("Logged in successfully!")
                else:
                    st.error(res.json().get("message", "Login failed."))


def side_nav(role):
    st.sidebar.title(f"{role} Dashboard")

    if role == "Teacher":
        section = st.sidebar.radio("Navigate", ["My Profile", "Upload Content", "Teacher Report Section", "Logout"])

        # Clear session state if leaving Teacher Report Section
        if section != "Teacher Report Section" and st.session_state.get("entered_teacher_report"):
            st.session_state.pop("selected_student", None)
            st.session_state.pop("selected_subject", None)
            st.session_state.pop("show_report", None)
            st.session_state.pop("entered_teacher_report", None)
            st.session_state.pop("fetched_students", None)

        return section

    else:
        return st.sidebar.radio("Navigate", ["My Profile", "Solve Doubts", "Take Quiz", "Quiz Feedback", "Reports", "Logout"])


def profile():
    st.subheader("Welcome")
    st.write(f"Hello, {st.session_state.get('name', '')}")

def upload_content():
    st.subheader("Upload Study Content")
    with st.form("content_form"):
        subject = st.text_input("Subject")
        student_class = st.text_input("Class")
        content_text = st.text_area("Content")
        file = st.file_uploader("Attach File (optional)")
        submit = st.form_submit_button("Upload")

        if submit:
            files = {"file": (file.name, file)} if file else {}
            data = {
                "teacher_id": st.session_state['user_id'],
                "subject": subject,
                "student_class": student_class,
                "content_text": content_text
            }
            res = requests.post(BASE_URL + "/upload_content", data=data, files=files)
            if res.status_code == 200:
                st.success("Content uploaded successfully.")
            else:
                st.error(res.json().get("message"))

def solve_doubt():
    st.subheader("Ask a Doubt (Text Only)")
    with st.form("doubt_form"):
        subject = st.text_input("Subject")
        question_text = st.text_area("Enter your doubt (text only)")
        submit = st.form_submit_button("Submit")

        if submit:
            student_id = st.session_state.get('student_id')
            if not student_id:
                st.error("Student ID not found in session.")
                return

            data = {
                "subject": subject,
                "question_text": question_text,
                "student_id": student_id
            }

            res = requests.post(BASE_URL + "/submit_doubt", data=data)
            if res.status_code == 200:
                st.success("Doubt solved successfully!")
                st.write("**Answer:**", res.json().get("answer", "No answer returned"))
            else:
                try:
                    st.error(res.json().get("message", "Failed to submit doubt."))
                except:
                    st.error("Unexpected error occurred.")


def take_quiz():
    st.subheader("Take a Quiz")

    student_id = st.session_state.get("user_id")
    if not student_id:
        st.error("You are not logged in. Please log in again.")
        return

    subject = st.text_input("Subject")  # allows typing any subject

    if st.button("Generate Quiz"):
        if not subject.strip():  # check if subject is empty
            st.error("Please enter a subject.")
            return

        # Safe API call
        res = requests.get(BASE_URL + "/generate_quiz", params={"subject": subject.strip(), "student_id": student_id})
        if res.status_code == 200:
            st.session_state["quiz_data"] = res.json()
            st.session_state["current_subject"] = subject.strip()
        else:
            st.error(res.json().get("message", "Failed to generate quiz."))

    quiz_data = st.session_state.get("quiz_data", None)
    if quiz_data:
        answers = []
        st.write("### Answer the following questions:")
        for q in quiz_data["questions"]:
            st.markdown(f"**Q:** {q['question']}")
            selected = st.radio("Select one:", q["options"], key=q["question"])
            answers.append({
                "question": q["question"],
                "selected_option": selected,
                "correct_answer": q.get("answer", "")  # must be returned by backend during quiz generation
            })

        if st.button("Submit Quiz"):
            payload = {
                "student_id": student_id,
                "subject": st.session_state.get("current_subject", "Unknown"),
                "answers": answers
            }
            submit_res = requests.post(BASE_URL + "/submit_quiz", json=payload)
            if submit_res.status_code == 200:
                st.success(f"Quiz submitted! Your score: {submit_res.json()['score_percent']}%")
            else:
                st.error("Failed to submit quiz.")


def view_feedback():
    st.subheader("Quiz Feedback")

    student_id = st.session_state.get("user_id")
    subject = st.text_input("Enter Subject")

    if st.button("Get Feedback"):
        res = requests.get(BASE_URL + "/quiz_feedback", params={"student_id": student_id, "subject": subject})
        if res.status_code == 200:
            feedback_list = res.json().get("feedback", [])

            if not feedback_list:
                st.info("No feedback found for this subject.")
                return

            for entry in feedback_list:
                st.markdown(f"### Subject: {entry.get('subject', 'N/A')}")
                st.write(f"**Score:** {entry.get('score', 'N/A')}%")

                st.markdown("**Incorrect Questions:**")
                for q in entry.get("incorrect_questions", []):
                    st.markdown(f"- **Q:** {q.get('question', 'Unknown')}")
                    st.markdown(f"  - Your answer: {q.get('your_answer', 'N/A')}")
                    st.markdown(f"  - Correct answer: {q.get('correct_answer', 'N/A')}")


                st.markdown("**Weak Topics to Focus On:**")
                for topic in entry.get("weak_topics", []):
                    st.markdown(f"- {topic}")

        else:
            st.error("Could not fetch feedback.")


def view_report():
    st.subheader("Quiz Performance Report")

    student_id = st.session_state.get("user_id")
    subject = st.text_input("Enter Subject for Report (leave blank for all):")

    if st.button("Get Report"):
        params = {"student_id": student_id}
        if subject.strip():
            params["subject"] = subject.strip()

        # Fetch Quiz Report
        res = requests.get(BASE_URL + "/quiz_report", params=params)
        if res.status_code == 200:
            data = res.json()
            st.markdown(f"### Report for: `{data['subject']}`")
            st.markdown(f"- **Total Quizzes Taken**: {data['total_quizzes']}")
            st.markdown(f"- **Average Score**: {data['average_score']}%")

            st.line_chart(data["scores"])
        else:
            st.error(res.json().get("message", "Failed to fetch report."))

        # --- Doubts Section ---
        st.markdown("---")
        st.subheader("Doubts Asked")

        doubt_params = {"student_id": student_id}
        if subject.strip():
            doubt_params["subject"] = subject.strip()

        doubt_res = requests.get(BASE_URL + "/get_doubts", params=doubt_params)
        if doubt_res.status_code == 200:
            doubts = doubt_res.json()
            if not doubts:
                st.info("No doubts asked for this subject.")
            else:
                for i, d in enumerate(doubts, 1):
                    st.markdown(f"**{i}. Subject:** {d['subject']}")
                    st.markdown(f"- Question: {d['question']}")
                    st.markdown(f"- Answer: {d['answer'] or 'Not answered yet'}")
        else:
            st.error("Failed to fetch doubts.")


def view_teacher_report():
    st.subheader("Teacher Report Section")

    # Track if we're in this section to clear it later
    st.session_state["entered_teacher_report"] = True

    class_name = st.text_input("Enter Class:")
    subject = st.text_input("Enter Subject:")

    if st.button("Fetch Students"):
        res = requests.get(BASE_URL + "/teacher_report", params={"class": class_name, "subject": subject})
        if res.status_code == 200:
            students = res.json().get("students", [])
            if not students:
                st.info("No students or reports found.")
                return

            st.session_state["fetched_students"] = students  # Save list
            st.session_state["selected_student"] = None  # clear previous student
            st.session_state["selected_subject"] = None
            st.session_state["show_report"] = False

        else:
            st.error("Failed to fetch student list.")

    # Display students list if available
    students = st.session_state.get("fetched_students", [])
    if students:
        st.write("### Students:")
        for stu in students:
            with st.expander(f"{stu['name']} (Avg Score: {stu['average_score']}%)"):
                with st.form(key=f"form_{stu['id']}"):
                    submitted = st.form_submit_button(f"View Full Report for {stu['name']}")
                    if submitted:
                        st.session_state["selected_student"] = stu["id"]
                        st.session_state["selected_subject"] = subject
                        st.session_state["show_report"] = True

    # Show student report & feedback if selected
    if st.session_state.get("show_report"):
        selected_id = st.session_state.get("selected_student")
        selected_sub = st.session_state.get("selected_subject")
        if selected_id and selected_sub:
            st.markdown("### 📈 Student Quiz Report:")
            show_student_report(selected_id, selected_sub)

            show_student_doubts(selected_id, selected_sub)



def show_student_report(student_id, subject):
    res = requests.get(BASE_URL + "/quiz_report", params={"student_id": student_id, "subject": subject})
    if res.status_code == 200:
        data = res.json()
        st.markdown(f"- **Total Quizzes**: {data['total_quizzes']}")
        st.markdown(f"- **Average Score**: {data['average_score']}%")
        st.line_chart(data["scores"])
    else:
        st.error("Error fetching report.")

def show_student_feedback(student_id, subject):
    res = requests.get(BASE_URL + "/quiz_feedback", params={"student_id": student_id, "subject": subject})
    if res.status_code == 200:
        feedback_list = res.json().get("feedback", [])
        if feedback_list:
            for entry in feedback_list:
                st.write(f"**Score:** {entry.get('score', 'N/A')}%")
                st.write("**Incorrect Questions:**")
                for q in entry.get("incorrect_questions", []):
                    st.markdown(f"- **Q:** {q.get('question', '')}")
                    st.markdown(f"  - Your answer: {q.get('your_answer', '')}")
                    st.markdown(f"  - Correct: {q.get('correct_answer', '')}")
                st.write("**Weak Topics:**")
                for topic in entry.get("weak_topics", []):
                    st.markdown(f"- {topic}")
        else:
            st.info("No feedback data.")
    else:
        st.error("Error fetching feedback.")

def show_student_doubts(student_id, subject):
    res = requests.get(BASE_URL + "/get_doubts", params={"student_id": student_id, "subject": subject})
    if res.status_code == 200:
        doubts = res.json()
        if doubts:
            st.markdown("### ❓ Doubts Asked:")
            for i, doubt in enumerate(doubts, 1):
                st.markdown(f"**{i}. Question:** {doubt['question']}")
                st.markdown(f"   - **Answer:** {doubt['answer'] or 'Not answered yet'}")
        else:
            st.info("No doubts found for this subject.")
    else:
        st.error("Error fetching doubts.")


def main():
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False
        st.session_state['role'] = None
        st.session_state['name'] = None
        st.session_state['user_id'] = None
        st.session_state['logout'] = False

    if st.session_state.get("logged_out"):
        st.session_state.clear()
        login_page()  
        return

    if not st.session_state['logged_in']:
        login_page()
        return

    role = st.session_state['role']
    choice = side_nav(role)

    if choice == "My Profile":
        profile()
    elif choice == "Upload Content" and role == "Teacher":
        upload_content()
    elif choice == "Solve Doubts" and role == "Student":
        solve_doubt()
    elif choice == "Take Quiz" and role == "Student":
        take_quiz()
    elif choice == "Quiz Feedback" and role == "Student":
        view_feedback()
    elif choice == "Reports" and role == "Student":
        view_report()
    elif choice == "Teacher Report Section" and role == "Teacher":
        view_teacher_report()
    elif choice == "Logout":
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.session_state["logged_out"] = True


if __name__ == '__main__':
    main()
