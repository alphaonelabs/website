from datetime import date, timedelta

from django.core.management.base import BaseCommand

from web.models import Challenge


class Command(BaseCommand):
    help = "Populate 52 weekly challenges."

    def handle(self, *args, **options):
        challenges_data = [
            {
                "title": "Learn 10 new vocabulary words",
                "description": "Expand your vocabulary by learning 10 new words and using them in sentences.",
            },
            {
                "title": "Solve 5 math puzzles",
                "description": "Challenge your brain by solving 5 math puzzles and explaining your thought process.",
            },
            {
                "title": "Read a short story",
                "description": "Read a short story and write a summary of its plot and characters.",
            },
            {
                "title": "Practice a new musical instrument for 30 minutes",
                "description": "Spend 30 minutes learning or practicing a musical instrument.",
            },
            {"title": "Write a short poem", "description": "Compose a short poem on any topic that inspires you."},
            {
                "title": "Learn a new coding concept",
                "description": "Study a new coding concept or language feature and create a small demo.",
            },
            {
                "title": "Complete a science experiment",
                "description": "Perform a simple science experiment and document your results.",
            },
            {
                "title": "Practice a foreign language conversation",
                "description": "Engage in a conversation in a foreign language or use language-learning apps.",
            },
            {
                "title": "Study a historical event",
                "description": "Research a historical event and share interesting facts or insights.",
            },
            {
                "title": "Create a simple piece of art",
                "description": "Draw, paint, or craft something creative and share a photo or description.",
            },
            {
                "title": "Do a brain teaser puzzle",
                "description": "Solve a brain teaser puzzle and describe how you approached it.",
            },
            {
                "title": "Learn about a new culture",
                "description": (
                    "Research a culture different from your own and share some of its traditions or customs."
                ),
            },
            {
                "title": "Write a letter to a pen pal",
                "description": "Draft a letter to a friend or pen pal discussing your interests and experiences.",
            },
            {"title": "Try a new recipe", "description": "Cook a new recipe and document the process and outcome."},
            {
                "title": "Watch an educational documentary",
                "description": "View a documentary and write a brief review or summary.",
            },
            {
                "title": "Review past notes on a challenging topic",
                "description": "Go over your notes on a topic you find challenging and highlight key points.",
            },
            {
                "title": "Complete a logic puzzle",
                "description": "Solve a logic puzzle and explain the reasoning behind your solution.",
            },
            {
                "title": "Write a summary of a book chapter",
                "description": "Read and summarize a chapter from a book you’re reading.",
            },
            {
                "title": "Explore a new educational website",
                "description": "Visit an educational website you haven’t used before and share your findings.",
            },
            {
                "title": "Practice mental math for 20 minutes",
                "description": "Dedicate 20 minutes to mental math exercises and record your progress.",
            },
            {
                "title": "Learn a fun fact about science",
                "description": "Discover an interesting scientific fact and research its background.",
            },
            {
                "title": "Take a virtual museum tour",
                "description": "Explore a museum online and share your favorite exhibit or artifact.",
            },
            {
                "title": "Study a famous inventor's life",
                "description": "Research the life and contributions of a famous inventor.",
            },
            {
                "title": "Solve a Sudoku puzzle",
                "description": "Complete a Sudoku puzzle and describe any strategies you used.",
            },
            {
                "title": "Learn 5 new words in a foreign language",
                "description": "Enhance your language skills by learning 5 new words with their meanings.",
            },
            {
                "title": "Practice mindfulness and meditation",
                "description": "Spend time practicing mindfulness or meditation and reflect on the experience.",
            },
            {
                "title": "Do a group study session",
                "description": "Collaborate with peers in a study session and discuss key topics.",
            },
            {
                "title": "Create a mind map for a subject",
                "description": "Organize your thoughts by creating a mind map on a subject of interest.",
            },
            {
                "title": "Research a current event",
                "description": "Investigate a recent news event and provide an overview of its impact.",
            },
            {
                "title": "Engage in a physical activity for brain health",
                "description": (
                    "Participate in any physical activity and reflect on its benefits for your cognitive skills."
                ),
            },
            {
                "title": "Do a memory challenge game",
                "description": "Play a memory game and share tips for improving memory retention.",
            },
            {
                "title": "Complete an online quiz on a subject",
                "description": "Take an online quiz and analyze your performance for improvement areas.",
            },
            {
                "title": "Watch a tutorial on a new skill",
                "description": "View a tutorial video and try to implement the demonstrated skill.",
            },
            {
                "title": "Practice typing speed",
                "description": "Work on increasing your typing speed and accuracy using online tools.",
            },
            {
                "title": "Solve a riddle",
                "description": "Challenge yourself with a riddle and explain your solution process.",
            },
            {
                "title": "Learn about a different country's traditions",
                "description": "Research traditions from another country and share interesting customs.",
            },
            {
                "title": "Practice drawing or doodling",
                "description": "Spend some time drawing or doodling to boost creativity.",
            },
            {"title": "Write a creative story", "description": "Craft a short, creative story in any genre you enjoy."},
            {
                "title": "Review and organize your notes",
                "description": "Take time to review your study materials and organize your notes effectively.",
            },
            {
                "title": "Engage in a science challenge experiment",
                "description": "Perform a small science experiment and document the procedure and outcome.",
            },
            {
                "title": "Learn a new fact about astronomy",
                "description": "Discover a fascinating fact about astronomy and explain its significance.",
            },
            {
                "title": "Participate in a discussion forum",
                "description": "Join an online discussion on a topic of interest and share your views.",
            },
            {
                "title": "Create flashcards for a topic",
                "description": "Develop a set of flashcards to help memorize key information about a subject.",
            },
            {
                "title": "Review a lesson from the past week",
                "description": "Reflect on the lessons learned during the past week and summarize them.",
            },
            {
                "title": "Watch a TED talk and write your thoughts",
                "description": "View a TED talk and write a brief reflection on its key messages.",
            },
            {
                "title": "Research a topic outside your comfort zone",
                "description": "Explore a subject you’re not familiar with and share your findings.",
            },
            {
                "title": "Try an online interactive learning game",
                "description": "Engage with an educational game and describe what you learned.",
            },
            {
                "title": "Write a reflection on what you learned this week",
                "description": "Summarize your achievements and insights from the week.",
            },
            {
                "title": "Teach a friend about a new concept",
                "description": "Explain a new idea or concept to a friend and discuss its applications.",
            },
            {
                "title": "Solve a challenging crossword puzzle",
                "description": "Complete a crossword puzzle and share strategies that helped you.",
            },
            {
                "title": "Review a subject you struggled with",
                "description": "Revisit a challenging subject and write about your progress or remaining questions.",
            },
            {
                "title": "Set a new learning goal for next week",
                "description": (
                    "Reflect on your progress and set a clear, achievable learning goal for the upcoming week."
                ),
            },
        ]

        start_date = date.today()
        for i, data in enumerate(challenges_data, start=1):
            challenge_start = start_date + timedelta(weeks=i - 1)
            challenge_end = challenge_start + timedelta(days=6)
            challenge, created = Challenge.objects.get_or_create(
                week_number=i,
                defaults={
                    "title": data["title"],
                    "description": data["description"],
                    "start_date": challenge_start,
                    "end_date": challenge_end,
                },
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"Challenge for week {i} created."))
            else:
                self.stdout.write(f"Challenge for week {i} already exists.")
