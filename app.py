from flask import Flask, render_template, redirect, url_for, flash, request
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField
from wtforms.validators import DataRequired, Email, EqualTo
from werkzeug.security import generate_password_hash, check_password_hash
import os

# Flask app setup
app = Flask(__name__)
app.config['SECRET_KEY'] = 'my-secret-key'  # Replace with a secure random string in production
base_dir = os.path.abspath(os.path.dirname(__file__))
instance_dir = os.path.join(base_dir, 'instance')
os.makedirs(instance_dir, exist_ok=True)  # Ensure instance directory exists
db_path = os.path.join(instance_dir, 'db.sqlite3').replace('\\', '/')  # Use forward slashes for SQLite URI
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['STATIC_FOLDER'] = 'static'

# Database setup
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)

class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    lessons = db.relationship('Lesson', backref='course', lazy=True)
    quizzes = db.relationship('Quiz', backref='course', lazy=True)

class Lesson(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)

class Quiz(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    question = db.Column(db.Text, nullable=False)
    correct_answer = db.Column(db.String(100), nullable=False)

class Enrollment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)

class Progress(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    lesson_id = db.Column(db.Integer, db.ForeignKey('lesson.id'), nullable=False)
    completed = db.Column(db.Boolean, default=False)

# Forms
class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class QuizForm(FlaskForm):
    answer = StringField('Your Answer', validators=[DataRequired()])
    submit = SubmitField('Submit Answer')

# Routes
@app.route('/')
def home():
    courses = Course.query.all()
    return render_template('home.html', courses=courses)

@app.route('/dashboard')
@login_required
def dashboard():
    all_courses = Course.query.all()
    enrollments = Enrollment.query.filter_by(user_id=current_user.id).all()
    enrolled_course_ids = [enrollment.course_id for enrollment in enrollments]
    enrolled_courses = Course.query.filter(Course.id.in_(enrolled_course_ids)).all()
    return render_template('dashboard.html', all_courses=all_courses, enrolled_courses=enrolled_courses)

@app.route('/courses/<int:course_id>/lessons')
@login_required
def view_lessons(course_id):
    course = Course.query.get_or_404(course_id)
    enrollment = Enrollment.query.filter_by(user_id=current_user.id, course_id=course.id).first()
    if not enrollment:
        flash('You must enroll in this course to view its lessons.', 'danger')
        return redirect(url_for('dashboard'))
    lessons = Lesson.query.filter_by(course_id=course.id).all()
    lesson_ids = [lesson.id for lesson in lessons]
    progress_entries = Progress.query.filter_by(user_id=current_user.id).filter(Progress.lesson_id.in_(lesson_ids)).all()
    lesson_progress = {progress.lesson_id: progress for progress in progress_entries}
    return render_template('lessons.html', course=course, lessons=lessons, lesson_progress=lesson_progress)

@app.route('/lessons/<int:lesson_id>/complete', methods=['POST'])
@login_required
def complete_lesson(lesson_id):
    lesson = Lesson.query.get_or_404(lesson_id)
    enrollment = Enrollment.query.filter_by(user_id=current_user.id, course_id=lesson.course_id).first()
    if not enrollment:
        flash('You must enroll in this course to mark lessons as completed.', 'danger')
        return redirect(url_for('dashboard'))
    progress = Progress.query.filter_by(user_id=current_user.id, lesson_id=lesson.id).first()
    if not progress:
        progress = Progress(user_id=current_user.id, lesson_id=lesson.id, completed=True)
        db.session.add(progress)
    else:
        progress.completed = True
    db.session.commit()
    flash(f'Marked "{lesson.title}" as completed!', 'success')
    return redirect(url_for('view_lessons', course_id=lesson.course_id))

@app.route('/courses/<int:course_id>/quizzes')
@login_required
def view_quizzes(course_id):
    course = Course.query.get_or_404(course_id)
    enrollment = Enrollment.query.filter_by(user_id=current_user.id, course_id=course.id).first()
    if not enrollment:
        flash('You must enroll in this course to view its quizzes.', 'danger')
        return redirect(url_for('dashboard'))
    quizzes = Quiz.query.filter_by(course_id=course.id).all()
    return render_template('quizzes.html', course=course, quizzes=quizzes)

@app.route('/quizzes/<int:quiz_id>/take', methods=['GET', 'POST'])
@login_required
def take_quiz(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    course = quiz.course
    enrollment = Enrollment.query.filter_by(user_id=current_user.id, course_id=course.id).first()
    if not enrollment:
        flash('You must enroll in this course to take quizzes.', 'danger')
        return redirect(url_for('dashboard'))
    form = QuizForm()
    if form.validate_on_submit():
        user_answer = form.answer.data.lower().strip()
        correct_answer = quiz.correct_answer.lower().strip()
        if user_answer == correct_answer:
            flash(f'Correct! You passed the quiz: "{quiz.title}".', 'success')
        else:
            flash(f'Wrong answer. The correct answer is "{quiz.correct_answer}".', 'danger')
        return redirect(url_for('view_quizzes', course_id=course.id))
    return render_template('take_quiz.html', quiz=quiz, form=form)

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data,
                    password=generate_password_hash(form.password.data))
        db.session.add(user)
        db.session.commit()
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and check_password_hash(user.password, form.password.data):
            login_user(user)
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        flash('Invalid email or password.', 'danger')
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully.', 'success')
    return redirect(url_for('home'))

@app.route('/courses/<int:course_id>/enroll')
@login_required
def enroll(course_id):
    course = Course.query.get_or_404(course_id)
    existing_enrollment = Enrollment.query.filter_by(user_id=current_user.id, course_id=course.id).first()
    if existing_enrollment:
        flash(f'You are already enrolled in {course.title}!', 'info')
        return redirect(url_for('dashboard'))
    enrollment = Enrollment(user_id=current_user.id, course_id=course.id)
    db.session.add(enrollment)
    db.session.commit()
    flash(f'Enrolled in {course.title}!', 'success')
    return redirect(url_for('dashboard'))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

if __name__ == '__main__':
    try:
        with app.app_context():
            db.create_all()
        print("Database created successfully!")
        app.run(debug=True)
    except Exception as e:
        print(f"Error creating database: {e}")