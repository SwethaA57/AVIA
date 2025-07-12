# models.py
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    institution = db.Column(db.String(100))
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    student_class = db.Column(db.String(50))

class QuizResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'))
    subject = db.Column(db.String(100))
    score_percent = db.Column(db.Float)
    submitted_answers = db.Column(db.JSON)
    correct_answers = db.Column(db.JSON)

class Content(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    institute_id = db.Column(db.Integer)
    teacher_id = db.Column(db.Integer)
    subject = db.Column(db.String(100))
    student_class = db.Column(db.String(50))
    content_text = db.Column(db.Text)
    file_path = db.Column(db.String(200))
