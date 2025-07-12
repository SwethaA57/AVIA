# Flask Backend

from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import os
from qa_model import answer_doubt
from models import db, QuizResult, Student, Content 


app = Flask(__name__)
CORS(app, supports_credentials=True)

# Config
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///ai_classroom.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Initialize db here (don't redefine db again)
db.init_app(app)

with app.app_context():
    db.create_all()

# === Models ===
class Teacher(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    institution = db.Column(db.String(100))
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))


class Doubt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer)
    subject = db.Column(db.String(100))
    question_text = db.Column(db.Text)
    file_path = db.Column(db.String(200))
    answer = db.Column(db.Text)

with app.app_context():
    db.create_all()

# === Authentication ===
@app.route('/register_teacher', methods=['POST'])
def register_teacher():
    data = request.get_json()
    if Teacher.query.filter_by(email=data['email']).first():
        return jsonify({"message": "Teacher already registered"}), 400
    new_teacher = Teacher(**data)
    db.session.add(new_teacher)
    db.session.commit()
    return jsonify({"message": "Teacher registered successfully"}), 201

@app.route('/register_student', methods=['POST'])
def register_student():
    data = request.get_json()
    if Student.query.filter_by(email=data['email']).first():
        return jsonify({"message": "Student already registered"}), 400
    new_student = Student(**data)
    db.session.add(new_student)
    db.session.commit()
    return jsonify({"message": "Student registered successfully"}), 201

@app.route('/login_teacher', methods=['POST'])
def login_teacher():
    data = request.get_json()
    teacher = Teacher.query.filter_by(email=data['email'], password=data['password']).first()
    if not teacher:
        return jsonify({"message": "Invalid login"}), 401
    return jsonify({
    "message": "Login successful",
    "name": teacher.name,
    "id": teacher.id
})


@app.route('/login_student', methods=['POST'])
def login_student():
    data = request.get_json()
    student = Student.query.filter_by(email=data['email'], password=data['password']).first()
    if not student:
        return jsonify({"message": "Invalid login"}), 401
    return jsonify({
    "message": "Login successful",
    "name": student.name,
    "id": student.id
    })


# === Upload Content ===
@app.route('/upload_content', methods=['POST'])
def upload_content():
    teacher_id = request.form.get('teacher_id')
    subject = request.form.get('subject')
    student_class = request.form.get('student_class')
    content_text = request.form.get('content_text')
    file = request.files.get('file')
    file_path = None

    if file:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(file_path)

    content = Content(
        teacher_id=teacher_id,
        subject=subject,
        student_class=student_class,
        content_text=content_text,
        file_path=file_path
    )
    db.session.add(content)
    db.session.commit()
    return jsonify({"message": "Content uploaded successfully"})

# === Submit Doubt ===
from qa_model import answer_doubt  # ensure this is at the top

@app.route('/submit_doubt', methods=['POST'])
def submit_doubt():
    student_id = request.form.get('student_id')
    subject = request.form.get('subject')
    question_text = request.form.get('question_text', "").strip()

    # Basic validation
    if not student_id:
        return jsonify({"message": "Student ID missing"}), 400
    if not subject or not question_text:
        return jsonify({"message": "Subject and question text are required"}), 400

    # Fetch content for the subject
    content_entry = Content.query.filter_by(subject=subject).first()
    if not content_entry or not content_entry.content_text.strip():
        return jsonify({"message": "No relevant study material found to answer your doubt."}), 404

    context = content_entry.content_text.strip()

    # Generate answer using AI
    try:
        answer = answer_doubt(context, question_text)
    except Exception as e:
        answer = f"I'm sorry, something went wrong while processing the answer: {str(e)}"

    # Save to database
    doubt = Doubt(
        student_id=student_id,
        subject=subject,
        question_text=question_text,
        file_path=None,
        answer=answer
    )
    db.session.add(doubt)
    db.session.commit()

    return jsonify({"message": "Doubt solved successfully", "answer": answer})


# === Student Doubts ===
@app.route('/get_doubts', methods=['GET'])
def get_doubts():
    student_id = request.args.get('student_id')
    subject = request.args.get('subject')  

    if not student_id:
        return jsonify({"message": "Student ID missing"}), 400

    query = Doubt.query.filter_by(student_id=student_id)
    if subject:
        query = query.filter_by(subject=subject)

    doubts = query.all()
    return jsonify([
        {
            "subject": d.subject,
            "question": d.question_text,
            "answer": d.answer
        } for d in doubts
    ])


# === Quiz Generation ===
from quiz_model import generate_quiz

@app.route('/generate_quiz', methods=['GET'])
def generate_quiz_endpoint():
    subject = request.args.get('subject')
    student_id = request.args.get('student_id')

    if not subject or not student_id:
        return jsonify({"message": "Missing subject or student ID"}), 400

    # Find the relevant content uploaded by any teacher for that subject
    content_entry = Content.query.filter_by(subject=subject).first()
    if not content_entry:
        return jsonify({"message": "No content found for this subject"}), 404

    # Generate quiz from the content
    quiz = generate_quiz(content_entry.content_text)
    return jsonify(quiz)

# --- Submit Quiz ---
from flask import request, jsonify
from models import db, QuizResult, Student
import datetime


@app.route('/submit_quiz', methods=['POST'])
def submit_quiz():
    data = request.get_json()
    student_id = data.get("student_id")
    subject = data.get("subject")
    answers = data.get("answers")  # list of {question, selected_option, correct_answer}

    if not all([student_id, subject, answers]):
        return jsonify({"message": "Missing data"}), 400

    total_questions = len(answers)
    correct_count = 0
    submitted_answers = []
    correct_answers = []

    for entry in answers:
        submitted_answers.append({
            "question": entry.get("question"),
            "selected": entry.get("selected_option")
        })
        correct_answers.append({
            "question": entry.get("question"),
            "answer": entry.get("correct_answer")
        })
        if entry.get("selected_option") == entry.get("correct_answer"):
            correct_count += 1

    score_percent = round((correct_count / total_questions) * 100, 2)

    # Save result
    result = QuizResult(
        student_id=student_id,
        subject=subject,
        score_percent=score_percent,
        submitted_answers=submitted_answers,
        correct_answers=correct_answers
    )
    db.session.add(result)
    db.session.commit()

    return jsonify({"message": "Quiz submitted successfully", "score_percent": score_percent})

# --- quiz_feedback ---
from flask import request, jsonify
from models import QuizResult
from keybert import KeyBERT
import json

kw_model = KeyBERT()

@app.route("/quiz_feedback", methods=["GET"])
def quiz_feedback():
    student_id = request.args.get("student_id")
    subject = request.args.get("subject")

    if not student_id:
        return jsonify({"message": "Missing student ID"}), 400

    query = QuizResult.query.filter_by(student_id=student_id)
    if subject:
        query = query.filter_by(subject=subject)

    results = query.order_by(QuizResult.id.desc()).all()
    if not results:
        return jsonify({"feedback": []})

    feedback_list = []
    for result in results:
        incorrect = []
        all_wrong_text = []

        for sub, correct in zip(result.submitted_answers, result.correct_answers):
            if sub.get("selected") != correct.get("answer"):
                incorrect.append({
                    "question": sub.get("question", "Unknown"),
                    "your_answer": sub.get("selected", "N/A"),
                    "correct_answer": correct.get("answer", "N/A")
                })

                all_wrong_text.append(correct.get("question", "Unknown"))

        # Extract weak topics using KeyBERT
        combined_wrong_text = ". ".join(all_wrong_text)
        keywords = kw_model.extract_keywords(combined_wrong_text, keyphrase_ngram_range=(1, 3), stop_words='english', top_n=5)
        weak_topics = [k[0] for k in keywords] if keywords else ["None – good job!"]

        feedback_list.append({
            "subject": result.subject,
            "score": result.score_percent,
            "incorrect_questions": incorrect,
            "weak_topics": weak_topics
        })

    return jsonify({"feedback": feedback_list})



# === Report ===
@app.route('/quiz_report', methods=['GET'])
def quiz_report():
    student_id = request.args.get('student_id')
    subject = request.args.get('subject') 

    if not student_id:
        return jsonify({"message": "Missing student ID"}), 400

    query = QuizResult.query.filter_by(student_id=student_id)
    if subject:
        query = query.filter_by(subject=subject)

    results = query.all()
    if not results:
        return jsonify({"message": "No quiz results found."}), 404

    total_quizzes = len(results)
    avg_score = round(sum(r.score_percent for r in results) / total_quizzes, 2)

    scores = [r.score_percent for r in results]

    report = {
        "total_quizzes": total_quizzes,
        "average_score": avg_score,
        "scores": scores,
        "subject": subject if subject else "All Subjects"
    }

    return jsonify(report)

@app.route("/teacher_report", methods=["GET"])
def teacher_report():
    class_name = request.args.get("class")
    subject = request.args.get("subject")

    if not class_name or not subject:
        return jsonify({"message": "Missing class or subject"}), 400

    # Get all students in the given class
    students = Student.query.filter_by(student_class=class_name).all()

    if not students:
        return jsonify({"students": []})

    student_reports = []
    for student in students:
        results = QuizResult.query.filter_by(student_id=student.id, subject=subject).all()
        if not results:
            continue
        scores = [r.score_percent for r in results]
        avg_score = round(sum(scores) / len(scores), 2) if scores else 0
        student_reports.append({
            "id": student.id,
            "name": student.name,
            "average_score": avg_score,
            "quizzes_taken": len(results)
        })

    return jsonify({"students": student_reports})


if __name__ == "__main__":
    app.run(debug=True)
