"""Management command to seed the database with sample topics, courses, and lessons."""

from django.core.management.base import BaseCommand

from learning.models import Course, Lesson, Topic

SEED_DATA = [
    {
        "topic": {
            "name": "Python Programming",
            "description": "Learn Python from the ground up – variables, functions, OOP, and more.",
            "difficulty": "beginner",
            "icon": "🐍",
        },
        "courses": [
            {
                "title": "Python Fundamentals",
                "description": "Core Python syntax and concepts for absolute beginners.",
                "difficulty": "beginner",
                "estimated_hours": 4.0,
                "lessons": [
                    {
                        "title": "Variables and Data Types",
                        "content": (
                            "Understand Python variables, integers, floats, strings, "
                            "booleans, and the `type()` function."
                        ),
                        "lesson_type": "theory",
                        "order": 1,
                        "xp_reward": 10,
                    },
                    {
                        "title": "Control Flow: if / elif / else",
                        "content": (
                            "Learn how to make decisions in Python using conditional "
                            "statements and comparison operators."
                        ),
                        "lesson_type": "theory",
                        "order": 2,
                        "xp_reward": 10,
                    },
                    {
                        "title": "Loops: for and while",
                        "content": (
                            "Iterate over sequences with `for` loops and repeat "
                            "actions with `while` loops."
                        ),
                        "lesson_type": "practice",
                        "order": 3,
                        "xp_reward": 15,
                    },
                    {
                        "title": "Functions and Scope",
                        "content": (
                            "Define reusable functions with `def`, understand "
                            "parameters, return values, and variable scope."
                        ),
                        "lesson_type": "theory",
                        "order": 4,
                        "xp_reward": 15,
                    },
                    {
                        "title": "Lists and Dictionaries",
                        "content": (
                            "Work with Python's most common data structures: "
                            "lists (ordered, mutable) and dicts (key-value pairs)."
                        ),
                        "lesson_type": "practice",
                        "order": 5,
                        "xp_reward": 20,
                    },
                ],
            },
            {
                "title": "Object-Oriented Python",
                "description": "Classes, inheritance, and design patterns in Python.",
                "difficulty": "intermediate",
                "estimated_hours": 6.0,
                "lessons": [
                    {
                        "title": "Classes and Objects",
                        "content": "Define classes, create objects, and use `__init__` constructors.",
                        "lesson_type": "theory",
                        "order": 1,
                        "xp_reward": 15,
                    },
                    {
                        "title": "Inheritance and Polymorphism",
                        "content": "Extend classes with inheritance and override methods for polymorphic behaviour.",
                        "lesson_type": "theory",
                        "order": 2,
                        "xp_reward": 20,
                    },
                    {
                        "title": "Special Methods (Dunder Methods)",
                        "content": "Implement `__str__`, `__repr__`, `__len__`, `__eq__` and other magic methods.",
                        "lesson_type": "practice",
                        "order": 3,
                        "xp_reward": 20,
                    },
                ],
            },
        ],
    },
    {
        "topic": {
            "name": "Web Development",
            "description": "Build dynamic web applications with HTML, CSS, JavaScript, and Django.",
            "difficulty": "intermediate",
            "icon": "🌐",
        },
        "courses": [
            {
                "title": "HTML & CSS Basics",
                "description": "Structure and style web pages from scratch.",
                "difficulty": "beginner",
                "estimated_hours": 3.0,
                "lessons": [
                    {
                        "title": "HTML Document Structure",
                        "content": "DOCTYPE, html, head, body, semantic tags (header, main, footer).",
                        "lesson_type": "theory",
                        "order": 1,
                        "xp_reward": 10,
                    },
                    {
                        "title": "CSS Selectors and the Box Model",
                        "content": "Selectors, specificity, margin, padding, border, and the CSS box model.",
                        "lesson_type": "theory",
                        "order": 2,
                        "xp_reward": 10,
                    },
                    {
                        "title": "Flexbox Layout",
                        "content": "Build responsive one-dimensional layouts using CSS Flexbox.",
                        "lesson_type": "practice",
                        "order": 3,
                        "xp_reward": 20,
                    },
                ],
            },
            {
                "title": "Django Web Framework",
                "description": "Build full-stack web apps with Python's batteries-included framework.",
                "difficulty": "intermediate",
                "estimated_hours": 8.0,
                "lessons": [
                    {
                        "title": "Django MTV Architecture",
                        "content": "Understand Models, Templates, and Views and how requests flow through Django.",
                        "lesson_type": "theory",
                        "order": 1,
                        "xp_reward": 15,
                    },
                    {
                        "title": "Models and the ORM",
                        "content": "Define database models and query the database using Django's ORM.",
                        "lesson_type": "theory",
                        "order": 2,
                        "xp_reward": 20,
                    },
                    {
                        "title": "Class-Based Views",
                        "content": "Use ListView, DetailView, CreateView and other generic CBVs.",
                        "lesson_type": "practice",
                        "order": 3,
                        "xp_reward": 20,
                    },
                ],
            },
        ],
    },
    {
        "topic": {
            "name": "Data Science",
            "description": "Analyse data, build models, and extract insights with Python.",
            "difficulty": "intermediate",
            "icon": "📊",
        },
        "courses": [
            {
                "title": "Introduction to Data Analysis",
                "description": "Explore and visualise data using pandas and matplotlib.",
                "difficulty": "beginner",
                "estimated_hours": 5.0,
                "lessons": [
                    {
                        "title": "NumPy Arrays",
                        "content": "Create and manipulate N-dimensional arrays with NumPy.",
                        "lesson_type": "theory",
                        "order": 1,
                        "xp_reward": 15,
                    },
                    {
                        "title": "Pandas DataFrames",
                        "content": "Load, clean, filter, and aggregate tabular data with pandas.",
                        "lesson_type": "practice",
                        "order": 2,
                        "xp_reward": 20,
                    },
                    {
                        "title": "Data Visualisation with Matplotlib",
                        "content": "Create line plots, bar charts, histograms, and scatter plots.",
                        "lesson_type": "practice",
                        "order": 3,
                        "xp_reward": 20,
                    },
                ],
            },
        ],
    },
    {
        "topic": {
            "name": "Machine Learning",
            "description": "Build predictive models and understand core ML algorithms.",
            "difficulty": "advanced",
            "icon": "🤖",
        },
        "courses": [
            {
                "title": "Supervised Learning Fundamentals",
                "description": "Linear regression, logistic regression, decision trees, and SVMs.",
                "difficulty": "intermediate",
                "estimated_hours": 10.0,
                "lessons": [
                    {
                        "title": "Linear Regression",
                        "content": "Fit a line to data by minimising mean squared error; understand bias-variance tradeoff.",
                        "lesson_type": "theory",
                        "order": 1,
                        "xp_reward": 20,
                    },
                    {
                        "title": "Logistic Regression & Classification",
                        "content": "Predict discrete class labels using the sigmoid function and cross-entropy loss.",
                        "lesson_type": "theory",
                        "order": 2,
                        "xp_reward": 20,
                    },
                    {
                        "title": "Decision Trees and Random Forests",
                        "content": "Build tree-based models and ensemble them into Random Forests.",
                        "lesson_type": "practice",
                        "order": 3,
                        "xp_reward": 25,
                    },
                    {
                        "title": "Model Evaluation Metrics",
                        "content": "Accuracy, precision, recall, F1-score, ROC-AUC, and cross-validation.",
                        "lesson_type": "quiz",
                        "order": 4,
                        "xp_reward": 15,
                    },
                ],
            },
        ],
    },
]


class Command(BaseCommand):
    help = "Seed the database with sample topics, courses, and lessons."

    def handle(self, *args, **options):
        created_topics = 0
        created_courses = 0
        created_lessons = 0

        for entry in SEED_DATA:
            topic_data = entry["topic"]
            topic, t_created = Topic.objects.get_or_create(
                name=topic_data["name"],
                defaults={
                    "description": topic_data["description"],
                    "difficulty": topic_data["difficulty"],
                    "icon": topic_data["icon"],
                },
            )
            if t_created:
                created_topics += 1

            for course_data in entry["courses"]:
                lessons_data = course_data.pop("lessons")
                course, c_created = Course.objects.get_or_create(
                    title=course_data["title"],
                    topic=topic,
                    defaults={**course_data},
                )
                if c_created:
                    created_courses += 1

                for lesson_data in lessons_data:
                    _, l_created = Lesson.objects.get_or_create(
                        title=lesson_data["title"],
                        course=course,
                        defaults={
                            "content": lesson_data["content"],
                            "lesson_type": lesson_data["lesson_type"],
                            "order": lesson_data["order"],
                            "xp_reward": lesson_data["xp_reward"],
                        },
                    )
                    if l_created:
                        created_lessons += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Seed complete: {created_topics} topics, "
                f"{created_courses} courses, {created_lessons} lessons created."
            )
        )
