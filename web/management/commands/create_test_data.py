import random
from datetime import timedelta
from decimal import Decimal

from allauth.account.models import EmailAddress
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.utils.text import slugify

from web.models import (
    Achievement,
    BlogComment,
    BlogPost,
    Challenge,
    ChallengeSubmission,
    Course,
    CourseMaterial,
    CourseProgress,
    Enrollment,
    ForumCategory,
    ForumReply,
    ForumTopic,
    Goods,
    Meme,
    PeerConnection,
    PeerMessage,
    Points,
    ProductImage,
    Profile,
    Review,
    Session,
    SessionAttendance,
    Storefront,
    StudyGroup,
    Subject,
    WaitingRoom,
)


def random_date_between(start_date, end_date):
    """Generate a random datetime between start_date and end_date"""
    delta = end_date - start_date
    random_seconds = random.randint(0, int(delta.total_seconds()))
    return start_date + timedelta(seconds=random_seconds)


class Command(BaseCommand):
    help = "Creates test data for all models in the application"

    def clear_data(self):
        """Clear all existing data from the models."""
        self.stdout.write("Clearing existing data...")
        models = [
            BlogComment,
            BlogPost,
            PeerMessage,
            PeerConnection,
            ForumReply,
            ForumTopic,
            ForumCategory,
            Achievement,
            Review,
            CourseMaterial,
            SessionAttendance,
            CourseProgress,
            Enrollment,
            Session,
            Course,
            Subject,
            Profile,
            User,
            Goods,
            Meme,
            ProductImage,
        ]
        for model in models:
            model.objects.all().delete()
            self.stdout.write(f"Cleared {model.__name__}")

    @transaction.atomic
    def handle(self, *args, **kwargs):
        self.stdout.write("Creating test data...")

        # Clear existing data
        self.clear_data()

        # Create test users (teachers and students)
        teachers = []
        for i in range(3):
            user = User.objects.create_user(
                username=f"teacher{i}",
                email=f"teacher{i}@example.com",
                password="testpass123",
                first_name=f"Teacher{i}",
                last_name="Smith",
                last_login=timezone.now(),
            )
            Profile.objects.filter(user=user).update(is_teacher=True)
            EmailAddress.objects.create(user=user, email=user.email, primary=True, verified=True)
            teachers.append(user)
            self.stdout.write(f"Created teacher: {user.username}")

        students = []
        for i in range(10):
            user = User.objects.create_user(
                username=f"student{i}",
                email=f"student{i}@example.com",
                password="testpass123",
                first_name=f"Student{i}",
                last_name="Doe",
                last_login=timezone.now(),
            )
            EmailAddress.objects.create(user=user, email=user.email, primary=True, verified=True)
            students.append(user)
            self.stdout.write(f"Created student: {user.username}")

        users = teachers + students

        # Create challenges first
        challenges = []
        for i in range(5):
            week_num = i + 1
            # Skip if week number already exists
            if Challenge.objects.filter(week_number=week_num).exists():
                continue

            challenge = Challenge.objects.create(
                title=f"Weekly Challenge {i + 1}",
                description=f"Description for challenge {i + 1}",
                week_number=week_num,
                start_date=timezone.now().date() - timedelta(days=14),  # Start from 2 weeks ago
                end_date=(timezone.now() + timedelta(days=7)).date(),
            )
            challenges.append(challenge)
            self.stdout.write(f"Created challenge: {challenge.title}, {challenge.start_date},- {challenge.end_date}")

        if not challenges:
            self.stdout.write(self.style.WARNING("No new challenges created, all week numbers already exist."))

        waiting_rooms = []
        for i in range(5):
            room = WaitingRoom.objects.create(
                title=f"Waiting Room {i + 1}",
                description=f"Description for waiting room {i + 1}",
                subject=f"Subject {i + 1}",
                topics=f"Topic1 Topic2 Topic{i + 1}",
                creator=random.choice(teachers),  # Assign a random teacher as the creator
                status="open",
            )
            waiting_rooms.append(room)
            self.stdout.write(f"Created waiting room: {room.title}")

        # Add participants to waiting rooms
        for room in waiting_rooms:
            participants = random.sample(students, k=random.randint(1, len(students)))
            room.participants.set(participants)
            room.save()
            self.stdout.write(f"Added participants to waiting room: {room.title}")

        # Date range for random dates (from 2 weeks ago to now)
        now = timezone.now()
        two_weeks_ago = now - timedelta(days=14)

        # Now create challenge submissions and points
        for student in students:
            challenge_list = list(Challenge.objects.all())
            if not challenge_list:
                self.stdout.write(f"No challenges found for student {student.username}, skipping challenge submissions")
            else:
                completed_challenges = random.sample(
                    challenge_list, min(random.randint(1, len(challenge_list)), len(challenge_list))
                )
                for i, challenge in enumerate(completed_challenges):
                    # Create submission (will auto-create points through save method)
                    submission = ChallengeSubmission.objects.create(
                        user=student,
                        challenge=challenge,
                        submission_text=f"Submission for challenge {challenge.week_number}",
                        points_awarded=random.randint(5, 20),
                    )

                    # Assign random date to the submission
                    random_date = random_date_between(two_weeks_ago, now)
                    submission.submitted_at = random_date
                    submission.save(update_fields=["submitted_at"])

                    self.stdout.write(
                        f"Created submission for {student.username} - "
                        f"Challenge {challenge.week_number} on {random_date.date()}"
                    )

                    # Find the points record created by the submission save method and update its date
                    points = (
                        Points.objects.filter(user=student, challenge=challenge, point_type="regular")
                        .order_by("-awarded_at")
                        .first()
                    )

                    if points:
                        points.awarded_at = random_date
                        points.save(update_fields=["awarded_at"])

                    # For testing streaks, artificially add streak records for some users
                    if i > 0 and random.random() < 0.7:  # 70% chance to have a streak
                        streak_len = i + 1
                        streak_points = Points.objects.create(
                            user=student,
                            challenge=None,
                            amount=0,
                            reason=f"Current streak: {streak_len}",
                            point_type="streak",
                        )

                        # Set streak date slightly after the submission date
                        streak_date = random_date + timedelta(minutes=random.randint(1, 30))
                        streak_points.awarded_at = streak_date
                        streak_points.save(update_fields=["awarded_at"])

                        self.stdout.write(
                            f"Created streak record for {student.username}: {streak_len} on {streak_date.date()}"
                        )

                        # Add bonus points for streak milestones
                        if streak_len % 5 == 0:
                            bonus = streak_len // 5 * 5
                            bonus_points = Points.objects.create(
                                user=student,
                                challenge=None,
                                amount=bonus,
                                reason=f"Streak milestone bonus ({streak_len} weeks)",
                                point_type="bonus",
                            )

                            # Set bonus date slightly after the streak record
                            bonus_date = streak_date + timedelta(minutes=random.randint(1, 15))
                            bonus_points.awarded_at = bonus_date
                            bonus_points.save(update_fields=["awarded_at"])

                            self.stdout.write(
                                f"Created bonus points for {student.username}:" "" f" {bonus} on {bonus_date.date()}"
                            )

        # Create additional random points for testing
        for user in User.objects.all():
            # Create random regular points
            for _ in range(random.randint(1, 5)):
                points_amount = random.randint(5, 50)
                points = Points.objects.create(
                    user=user, amount=points_amount, reason="Test data - Random activity points", point_type="regular"
                )

                # Assign random date
                random_date = random_date_between(two_weeks_ago, now)
                points.awarded_at = random_date
                points.save(update_fields=["awarded_at"])
                self.stdout.write(f"Created {points_amount} random points for {user.username} on {random_date.date()}")

        # Create friend connections for leaderboards
        for student in students:
            # Create friend leaderboard for each student
            # Add random friends (from students already connected via PeerConnection)
            # Get connected friends directly
            friends = User.objects.filter(
                Q(sent_connections__receiver=student, sent_connections__status="accepted")
                | Q(received_connections__sender=student, received_connections__status="accepted")
            ).distinct()

            if friends:
                points = Points.objects.create(
                    user=student,
                    amount=friends.count(),  # Points for friend connections
                    reason=f"Connected with {friends.count()} peers",
                    challenge=None,
                )

                # Assign random date
                random_date = random_date_between(two_weeks_ago, now)
                points.awarded_at = random_date
                points.save(update_fields=["awarded_at"])

                self.stdout.write(
                    f"Created friend record for {student.username} with "
                    f"{len(friends)} friends on {random_date.date()}"
                )

        # Create entries for existing users
        users = User.objects.all()
        for user in users:
            # Random score between 100 and 1000
            score = random.randint(100, 1000)
            points = Points.objects.create(
                user=user,
                amount=score,
                reason="Test data - Random points",
                challenge=challenges[0] if challenges else None,
            )

            # Assign random date
            random_date = random_date_between(two_weeks_ago, now)
            points.awarded_at = random_date
            points.save(update_fields=["awarded_at"])

            self.stdout.write(f"Created {score} points for {user.username} on {random_date.date()}")

        self.stdout.write(f"Created {len(users)} leaderboard entries!")

        # Create subjects
        subjects = []
        subject_data = [
            ("Programming", "Learn coding", "fas fa-code"),
            ("Mathematics", "Master math concepts", "fas fa-calculator"),
            ("Science", "Explore scientific concepts", "fas fa-flask"),
            ("Languages", "Learn new languages", "fas fa-language"),
        ]

        for name, desc, icon in subject_data:
            subject = Subject.objects.create(name=name, slug=slugify(name), description=desc, icon=icon)
            subjects.append(subject)
            self.stdout.write(f"Created subject: {subject.name}")

        # Create courses
        courses = []
        levels = ["beginner", "intermediate", "advanced"]
        for i in range(10):
            course = Course.objects.create(
                title=f"Test Course {i}",
                slug=f"test-course-{i}",
                teacher=random.choice(teachers),
                description="# Course Description\n\nThis is a test course.",
                learning_objectives="# Learning Objectives\n\n- Objective 1\n- Objective 2",
                prerequisites="# Prerequisites\n\nBasic knowledge required",
                price=Decimal(random.randint(50, 200)),
                max_students=random.randint(10, 50),
                subject=random.choice(subjects),
                level=random.choice(levels),
                status="published",
                allow_individual_sessions=random.choice([True, False]),
                invite_only=random.choice([True, False]),
            )
            courses.append(course)
            self.stdout.write(f"Created course: {course.title}")

        # Create sessions
        sessions = []
        now = timezone.now()
        for course in courses:
            for i in range(5):
                start_time = now + timedelta(days=i * 7)
                is_virtual = random.choice([True, False])
                session = Session.objects.create(
                    course=course,
                    title=f"Session {i + 1}",
                    description=f"Description for session {i + 1}",
                    start_time=start_time,
                    end_time=start_time + timedelta(hours=2),
                    price=Decimal(random.randint(20, 50)),
                    is_virtual=is_virtual,
                    meeting_link="https://meet.example.com/test" if is_virtual else "",
                    location="" if is_virtual else "Test Location",
                )
                sessions.append(session)
            self.stdout.write(f"Created sessions for course: {course.title}")

        # Create enrollments and progress
        for student in students:
            # Get list of courses student isn't enrolled in yet
            enrolled_courses = set(Enrollment.objects.filter(student=student).values_list("course_id", flat=True))
            available_courses = [c for c in courses if c.id not in enrolled_courses]

            # Enroll in random courses
            for _ in range(min(random.randint(1, 3), len(available_courses))):
                course = random.choice(available_courses)
                available_courses.remove(course)  # Remove to avoid selecting again

                enrollment = Enrollment.objects.create(student=student, course=course, status="approved")

                # Create course progress
                progress = CourseProgress.objects.create(enrollment=enrollment)
                course_sessions = Session.objects.filter(course=course)
                completed_sessions = random.sample(list(course_sessions), random.randint(0, course_sessions.count()))
                progress.completed_sessions.add(*completed_sessions)

                # Create session attendance
                for session in completed_sessions:
                    SessionAttendance.objects.create(student=student, session=session, status="completed")

                self.stdout.write(f"Created enrollment for {student.username} in {course.title}")

        # Create course materials
        material_types = ["video", "document", "quiz", "assignment"]
        for course in courses:
            for i in range(3):
                CourseMaterial.objects.create(
                    course=course,
                    title=f"Material {i + 1}",
                    description=f"Description for material {i + 1}",
                    material_type=random.choice(material_types),
                    session=random.choice(sessions) if random.choice([True, False]) else None,
                    external_url="https://localhost/default-material",  # Ensuring NOT NULL constraint
                )
            self.stdout.write(f"Created materials for course: {course.title}")

        # Create achievements
        for student in students:
            for _ in range(random.randint(1, 3)):
                Achievement.objects.create(
                    student=student,
                    course=random.choice(courses),
                    title=f"Achievement for {student.username}",
                    description="Completed a milestone",
                )

        # Create reviews
        for student in students:
            # Get courses the student is enrolled in but hasn't reviewed yet
            enrolled_courses = set(Enrollment.objects.filter(student=student).values_list("course_id", flat=True))
            reviewed_courses = set(Review.objects.filter(student=student).values_list("course_id", flat=True))
            available_courses = [c for c in courses if c.id in enrolled_courses and c.id not in reviewed_courses]

            # Create reviews for random courses
            for _ in range(min(random.randint(1, 3), len(available_courses))):
                random_date = random_date_between(two_weeks_ago, now)
                course = random.choice(available_courses)
                available_courses.remove(course)  # Remove to avoid selecting again

                is_featured = random.choice([True, False])

                Review.objects.create(
                    student=student,
                    course=course,
                    rating=random.randint(3, 5),
                    comment="Great course!",
                    is_featured=is_featured,
                )
                self.stdout.write(
                    f"Created review, student: {student}, course: {course},"
                    "featured: {is_featured}, review: Great course!"
                )

        # Create forum categories and topics
        categories = []
        for i in range(3):
            category = ForumCategory.objects.create(
                name=f"Category {i + 1}", slug=f"category-{i + 1}", description=f"Description for category {i + 1}"
            )
            categories.append(category)

            # Create topics in each category
            for j in range(3):
                topic = ForumTopic.objects.create(
                    category=category,
                    title=f"Topic {j + 1}",
                    content=f"Content for topic {j + 1}",
                    author=random.choice(students + teachers),
                    github_issue_url="https://github.com/",
                    github_milestone_url="https://github.com/",
                )

                # Create replies
                for _ in range(random.randint(1, 5)):
                    ForumReply.objects.create(
                        topic=topic, content="This is a reply", author=random.choice(students + teachers)
                    )

        # Create peer connections and messages
        for student in students:
            # Get list of students not already connected with
            connected_peers = set(PeerConnection.objects.filter(sender=student).values_list("receiver_id", flat=True))
            connected_peers.update(PeerConnection.objects.filter(receiver=student).values_list("sender_id", flat=True))
            available_peers = [s for s in students if s != student and s.id not in connected_peers]

            # Create connections with random peers
            for _ in range(min(random.randint(1, 3), len(available_peers))):
                peer = random.choice(available_peers)
                available_peers.remove(peer)  # Remove to avoid selecting again

                PeerConnection.objects.create(sender=student, receiver=peer, status="accepted")

                # Create messages between these peers
                for _ in range(random.randint(1, 5)):
                    PeerMessage.objects.create(sender=student, receiver=peer, content="Test message")

        # Create study groups
        for course in courses:
            group = StudyGroup.objects.create(
                name=f"Study Group for {course.title}",
                description="A group for studying together",
                course=course,
                creator=random.choice(students),
                max_members=random.randint(5, 15),
            )
            # Add random members
            members = random.sample(students, random.randint(2, 5))
            group.members.add(*members)

        # Create blog posts and comments
        for teacher in teachers:
            for i in range(random.randint(1, 3)):
                post = BlogPost.objects.create(
                    title=f"Blog Post {i + 1} by {teacher.username}",
                    slug=f"blog-post-{i + 1}-by-{teacher.username}",
                    author=teacher,
                    content="# Test Content\n\nThis is a test blog post.",
                    status="published",
                    published_at=timezone.now(),
                )

                # Create comments
                for _ in range(random.randint(1, 5)):
                    BlogComment.objects.create(
                        post=post, author=random.choice(students), content="Great post!", is_approved=True
                    )

        # Create test storefronts
        storefronts = []
        for teacher in teachers:
            storefront = Storefront.objects.create(
                teacher=teacher,
                name=f"Storefront for {teacher.username}",
                description=f"Description for storefront of {teacher.username}",
                is_active=True,
            )
            storefronts.append(storefront)
            self.stdout.write(f"Created storefront: {storefront.name}")

        # Create test products (goods)
        goods = []
        goods_data = [
            {
                "name": "Algebra Basics Workbook",
                "description": "A comprehensive workbook for learning algebra basics.",
                "price": Decimal("19.99"),
                "discount_price": Decimal("14.99"),
                "stock": 100,
                "product_type": "physical",
                "category": "Books",
                "is_available": True,
                "storefront": random.choice(storefronts),
            },
            {
                "name": "Python Programming eBook",
                "description": "An in-depth guide to Python programming.",
                "price": Decimal("29.99"),
                "discount_price": Decimal("24.99"),
                "product_type": "digital",
                "file": None,  # Add a valid file path if needed
                "category": "eBooks",
                "is_available": True,
                "storefront": random.choice(storefronts),
            },
            {
                "name": "Science Experiment Kit",
                "description": "A kit for conducting various science experiments.",
                "price": Decimal("39.99"),
                "stock": 50,
                "product_type": "physical",
                "category": "Kits",
                "is_available": True,
                "storefront": random.choice(storefronts),
            },
        ]

        for data in goods_data:
            product = Goods.objects.create(**data)
            goods.append(product)
            self.stdout.write(f"Created product: {product.name}")

        # Create product images
        for product in goods:
            for i in range(2):
                ProductImage.objects.create(
                    goods=product,
                    image="path/to/image.jpg",
                    alt_text=f"Image {i + 1} for {product.name}",
                )
            self.stdout.write(f"Created images for product: {product.name}")

        # Create educational memes with random users
        self.create_meme_test_data(subjects, users)

        self.stdout.write(self.style.SUCCESS("Successfully created test data"))

    def create_meme_test_data(self, subjects: list[Subject], users: list[User]) -> None:
        """Create test data for educational memes."""
        self.stdout.write("Creating educational meme test data...")

        # Define meme data for various subjects
        meme_data = [
            {
                "subject_name": "Mathematics",
                "description": "The study of numbers, quantities, and shapes",
                "icon": "fas fa-square-root-alt",
                "memes": [
                    {
                        "title": "When You Finally Solve That Math Problem",
                        "caption": "The feeling when you've been stuck on a calculus problem for"
                        " hours and finally get it right.",
                        "image": "memes/math_eureka.jpg",
                    },
                    {
                        "title": "Algebra vs. Real World Problems",
                        "caption": "When you can solve complex equations but can't figure out how to adult.",
                        "image": "memes/algebra_vs_life.jpg",
                    },
                ],
            },
            {
                "subject_name": "Computer Science",
                "description": "The study of computers and computational systems",
                "icon": "fas fa-laptop-code",
                "memes": [
                    {
                        "title": "Debugging Be Like",
                        "caption": "When you've spent all day looking for a bug and it was just a missing semicolon.",
                        "image": "memes/debugging_semicolon.png",
                    },
                    {
                        "title": "Python vs JavaScript",
                        "caption": "The eternal debate among programmers.",
                        "image": "memes/python_vs_js.png",
                    },
                ],
            },
            {
                "subject_name": "Physics",
                "description": "The study of matter, energy, and the interaction between them",
                "icon": "fas fa-atom",
                "memes": [
                    {
                        "title": "Newton's Third Law in Real Life",
                        "caption": "For every action, there is an equal and opposite reaction. "
                        "Especially when messing with cats.",
                        "image": "memes/newton_cat.gif",
                    },
                    {
                        "title": "Schrodinger's Cat Explained",
                        "caption": "When the cat is both alive and dead until you open the box"
                        " - quantum physics at its finest.",
                        "image": "memes/schrodinger_cat.jpg",
                    },
                ],
            },
            {
                "subject_name": "Biology",
                "description": "The study of living organisms",
                "icon": "fas fa-dna",
                "memes": [
                    {
                        "title": "Mitochondria is the Powerhouse of the Cell",
                        "caption": "The one thing everyone remembers from biology class.",
                        "image": "memes/mitochondria_powerhouse.jpg",
                    },
                    {
                        "title": "Evolution of Humans",
                        "caption": "From apes to smartphone zombies - the missing link is WiFi.",
                        "image": "memes/evolution_wifi.jpg",
                    },
                ],
            },
            {
                "subject_name": "History",
                "description": "The study of past events",
                "icon": "fas fa-landmark",
                "memes": [
                    {
                        "title": "History Students During Exams",
                        "caption": "When you need to remember hundreds of dates and events for your history final.",
                        "image": "memes/history_dates.png",
                    },
                    {
                        "title": "When Your History Teacher Says 'Pop Quiz'",
                        "caption": "Sudden panic when you realize you haven't memorized all those important dates.",
                        "image": "memes/history_pop_quiz.png",
                    },
                ],
            },
        ]

        # For each subject, create or get the subject and add memes
        for subject_data in meme_data:
            # Find or create the subject
            subject_name = subject_data["subject_name"]
            subject_obj = None

            # Try to find the subject in the existing subjects
            for s in subjects:
                if s.name == subject_name:
                    subject_obj = s
                    break

            # If subject doesn't exist, create it
            if not subject_obj:
                subject_obj = Subject.objects.create(
                    name=subject_name,
                    slug=slugify(subject_name),
                    description=subject_data.get("description", f"Study of {subject_name}"),
                    icon=subject_data.get("icon", "fas fa-graduation-cap"),
                    order=len(subjects) + 1,
                )
                subjects.append(subject_obj)
                self.stdout.write(f"Created new subject: {subject_obj.name}")

            # Create memes for this subject
            for meme_info in subject_data["memes"]:
                # Select a random user as uploader
                uploader = random.choice(users)

                # Generate a random date within the last month
                random_date = timezone.now() - timedelta(days=random.randint(0, 30))

                # Create the meme
                meme = Meme.objects.create(
                    title=meme_info["title"],
                    subject=subject_obj,
                    caption=meme_info["caption"],
                    image=meme_info["image"],
                    uploader=uploader,
                    slug=slugify(meme_info["title"]),
                    created_at=random_date,
                    updated_at=random_date,
                )

                self.stdout.write(f"Created meme: {meme.title} (uploaded by {uploader.username})")
