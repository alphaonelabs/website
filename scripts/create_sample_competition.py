"""
Example script to create a sample competition with rewards.

This demonstrates how to use the Competitions feature programmatically.

Run from Django shell:
    python manage.py shell < scripts/create_sample_competition.py

Or in Django shell:
    exec(open('scripts/create_sample_competition.py').read())
"""

from datetime import timedelta

from django.contrib.auth.models import User
from django.utils import timezone

from web.models import Challenge, Competition, CompetitionReward

# Create a sample competition
competition = Competition.objects.create(
    title="Summer Coding Challenge 2025",
    description="""
    Join our Summer Coding Challenge and compete with fellow students!
    Complete challenges to earn points and climb the leaderboard.
    Top performers will receive amazing rewards including scholarships and premium access.
    """,
    start_date=timezone.now(),
    end_date=timezone.now() + timedelta(days=60),
    status="active",
    max_participants=100,
    entry_fee_points=25,
    rules="""
    1. All participants must complete at least 3 challenges to be eligible for rewards
    2. Challenges must be completed before the competition end date
    3. Plagiarism will result in disqualification
    4. Be respectful to other participants
    5. Have fun and learn!
    """,
)

print(f"Created competition: {competition.title}")

# Create some sample challenges (if they don't exist)
challenges = []
for i in range(1, 6):
    challenge, created = Challenge.objects.get_or_create(
        title=f"Coding Challenge {i}",
        defaults={
            "description": f"Complete this coding challenge to earn points in the competition!",
            "challenge_type": "one_time",
            "start_date": timezone.now().date(),
            "end_date": (timezone.now() + timedelta(days=60)).date(),
        },
    )
    challenges.append(challenge)
    if created:
        print(f"Created challenge: {challenge.title}")

# Add challenges to competition
competition.challenges.set(challenges)
print(f"Added {len(challenges)} challenges to competition")

# Create rewards
rewards = [
    {
        "reward_type": "scholarship",
        "name": "$1000 Scholarship",
        "description": "Full scholarship for the top performer",
        "position": 1,
        "quantity": 1,
        "value": 1000.00,
    },
    {
        "reward_type": "scholarship",
        "name": "$500 Scholarship",
        "description": "Scholarship for 2nd and 3rd place",
        "position": 2,
        "quantity": 2,
        "value": 500.00,
    },
    {
        "reward_type": "premium_subscription",
        "name": "3-Month Premium Access",
        "description": "Premium subscription for positions 4-10",
        "position": 4,
        "quantity": 7,
        "subscription_months": 3,
    },
    {
        "reward_type": "points",
        "name": "500 Bonus Points",
        "description": "Bonus points for positions 11-20",
        "position": 11,
        "quantity": 10,
        "points_amount": 500,
    },
    {
        "reward_type": "certificate",
        "name": "Certificate of Achievement",
        "description": "Digital certificate for all participants who complete 3+ challenges",
        "position": 21,
        "quantity": 100,
    },
]

for reward_data in rewards:
    reward = CompetitionReward.objects.create(competition=competition, **reward_data)
    print(f"Created reward: {reward.name} for position {reward.position}")

print("\n" + "=" * 60)
print("Sample competition created successfully!")
print("=" * 60)
print(f"Competition ID: {competition.id}")
print(f"Title: {competition.title}")
print(f"Status: {competition.status}")
print(f"Challenges: {competition.challenges.count()}")
print(f"Rewards: {competition.rewards.count()}")
print(f"\nView at: /competitions/{competition.id}/")
print("=" * 60)
