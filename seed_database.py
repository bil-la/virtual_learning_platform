from app import app, db, Course, Lesson, Quiz

with app.app_context():
    # Add courses
    course1 = Course(title="Python Basics", description="Learn Python programming from scratch.")
    course2 = Course(title="Web Development", description="Build websites with HTML, CSS, and JavaScript.")
    db.session.add(course1)
    db.session.add(course2)
    db.session.commit()

    # Add lessons
    lesson1 = Lesson(course_id=course1.id, title="Introduction to Python", content="Learn the basics of Python syntax.")
    lesson2 = Lesson(course_id=course1.id, title="Variables and Data Types", content="Understand variables and data types in Python.")
    lesson3 = Lesson(course_id=course2.id, title="HTML Basics", content="Introduction to HTML and its structure.")
    db.session.add(lesson1)
    db.session.add(lesson2)
    db.session.add(lesson3)
    db.session.commit()

    # Add quizzes
    quiz1 = Quiz(course_id=course1.id, title="Python Quiz 1", question="What is the output of print(2 + 3)?", correct_answer="5")
    quiz2 = Quiz(course_id=course2.id, title="HTML Quiz 1", question="What tag is used to create a paragraph?", correct_answer="p")
    db.session.add(quiz1)
    db.session.add(quiz2)
    db.session.commit()

exit()