from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from web.models import Flashcard, FlashcardDeck


class Command(BaseCommand):
    help = "Create sample flashcard data for demonstration"

    def handle(self, *args, **options):
        # Get or create admin user
        user, created = User.objects.get_or_create(
            username="admin", defaults={"email": "admin@example.com", "is_staff": True, "is_superuser": True}
        )
        if created:
            user.set_password("admin123")
            user.save()

        # Create Python Programming deck
        python_deck, created = FlashcardDeck.objects.get_or_create(
            name="Python Programming Basics",
            creator=user,
            defaults={"description": "Essential concepts for learning Python programming", "is_public": True},
        )

        if created:
            python_cards = [
                (
                    "What is Python?",
                    "Python is a high-level, interpreted programming language "
                    "known for its simple syntax and readability.",
                ),
                ("What does 'print()' do?", "The print() function displays output to the console or terminal."),
                (
                    "How do you create a variable in Python?",
                    "You create a variable by assigning a value: variable_name = value",
                ),
                (
                    "What is a list in Python?",
                    "A list is an ordered collection of items that can be changed (mutable). Example: [1, 2, 3]",
                ),
                (
                    "What is the difference between '==' and 'is'?",
                    "'==' compares values, while 'is' compares object identity (memory location).",
                ),
                (
                    "What is a function?",
                    "A function is a reusable block of code that performs a specific task. Defined with 'def'.",
                ),
                (
                    "What is indentation used for in Python?",
                    "Indentation defines code blocks and scope, replacing braces used in other languages.",
                ),
                (
                    "What is a dictionary?",
                    "A dictionary is an unordered collection of key-value pairs. Example: {'key': 'value'}",
                ),
            ]

            for i, (front, back) in enumerate(python_cards, 1):
                Flashcard.objects.create(deck=python_deck, front_text=front, back_text=back, order=i)

        # Create Math deck
        math_deck, created = FlashcardDeck.objects.get_or_create(
            name="Basic Mathematics",
            creator=user,
            defaults={"description": "Fundamental math concepts and formulas", "is_public": True},
        )

        if created:
            math_cards = [
                ("What is the Pythagorean theorem?", "a² + b² = c², where c is the hypotenuse of a right triangle."),
                ("What is the quadratic formula?", "x = (-b ± √(b²-4ac)) / 2a"),
                ("What is the area of a circle?", "A = πr², where r is the radius"),
                ("What is the slope formula?", "m = (y₂ - y₁) / (x₂ - x₁)"),
                (
                    "What is the definition of a prime number?",
                    "A natural number greater than 1 that has no positive divisors other than 1 and itself.",
                ),
                ("What is the derivative of x²?", "2x"),
                ("What is the sum of angles in a triangle?", "180 degrees or π radians"),
                ("What is the distance formula?", "d = √((x₂-x₁)² + (y₂-y₁)²)"),
            ]

            for i, (front, back) in enumerate(math_cards, 1):
                Flashcard.objects.create(deck=math_deck, front_text=front, back_text=back, order=i)

        # Create History deck
        history_deck, created = FlashcardDeck.objects.get_or_create(
            name="World History Facts",
            creator=user,
            defaults={"description": "Important dates and events in world history", "is_public": True},
        )

        if created:
            history_cards = [
                ("When did World War II end?", "September 2, 1945"),
                ("Who was the first person to walk on the moon?", "Neil Armstrong on July 20, 1969"),
                ("When was the Declaration of Independence signed?", "July 4, 1776"),
                ("What year did the Berlin Wall fall?", "1989"),
                ("Who invented the printing press?", "Johannes Gutenberg around 1440"),
                ("When did the Industrial Revolution begin?", "Mid-18th century (around 1760)"),
                ("What empire was ruled by Julius Caesar?", "The Roman Empire"),
                ("When did the French Revolution begin?", "1789"),
            ]

            for i, (front, back) in enumerate(history_cards, 1):
                Flashcard.objects.create(deck=history_deck, front_text=front, back_text=back, order=i)

        # Create a private deck
        private_deck, created = FlashcardDeck.objects.get_or_create(
            name="Personal Study Notes",
            creator=user,
            defaults={"description": "My private study notes - not visible to others", "is_public": False},
        )

        if created:
            private_cards = [
                ("What is my password recovery question?", "Name of my first pet"),
                ("Important meeting reminder", "Team standup every Monday at 9 AM"),
                ("Study schedule", "Math: Mon/Wed/Fri, History: Tue/Thu, Programming: Daily"),
            ]

            for i, (front, back) in enumerate(private_cards, 1):
                Flashcard.objects.create(deck=private_deck, front_text=front, back_text=back, order=i)

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully created sample flashcard data:\n"
                f"- {python_deck.name}: {python_deck.card_count} cards\n"
                f"- {math_deck.name}: {math_deck.card_count} cards\n"
                f"- {history_deck.name}: {history_deck.card_count} cards\n"
                f"- {private_deck.name}: {private_deck.card_count} cards"
            )
        )
