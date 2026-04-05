# Competitions Feature

The Competitions feature allows administrators to create educational competitions with rewards, encouraging student participation and achievement.

## Overview

Competitions can include multiple challenges and offer various types of rewards such as scholarships, premium subscriptions, merchandise, points, badges, and certificates.

## Key Components

### Models

#### Competition
- **Title & Description**: Competition information
- **Dates**: Start and end dates for the competition
- **Status**: `upcoming`, `active`, `ended`, or `archived`
- **Challenges**: Multiple challenges can be associated with a competition
- **Entry Fee**: Optional points required to join (0 for free)
- **Max Participants**: Optional limit on number of participants

#### CompetitionReward
- **Types**: scholarship, premium_subscription, merchandise, points, badge, certificate, goods
- **Position**: Rank required to win (1 for first place, etc.)
- **Type-specific fields**:
  - Scholarships: monetary value
  - Subscriptions: duration in months
  - Points: points amount
  - Merchandise: link to Goods item

#### CompetitionParticipant
- Tracks user participation in competitions
- Auto-calculates score based on challenge submissions
- Maintains rank and last submission time
- Stores claimed rewards

## Usage

### Admin Interface

1. **Create a Competition**:
   - Go to Django Admin → Competitions → Add Competition
   - Set title, description, dates, and status
   - Optionally set max participants and entry fee
   - Add challenges to the competition

2. **Add Rewards**:
   - Use the inline reward form when creating/editing a competition
   - Set reward type, position, and type-specific details
   - Specify quantity available for each reward

3. **Monitor Participants**:
   - View participants in the competition admin
   - Use "Update scores and ranks" action to recalculate rankings
   - Award rewards when competition ends

### User Experience

1. **Browse Competitions**: `/competitions/`
   - Filter by status (all, upcoming, active, ended, archived)
   - View competition cards with key information

2. **Join a Competition**: `/competitions/<id>/join/`
   - Must be logged in
   - Competition must be active or upcoming
   - Must have sufficient points if entry fee required
   - Cannot join if already participating

3. **View Competition Details**: `/competitions/<id>/`
   - See full competition information
   - View rewards, challenges, and leaderboard
   - Check personal progress if participating

4. **View Leaderboard**: `/competitions/<id>/leaderboard/`
   - Full rankings of all participants
   - Shows rank, username, score, join date, and last activity

## Automatic Features

### Score Updates
- When a user submits a challenge that's part of an active competition, their participant score automatically updates
- Ranks are recalculated after score updates

### Reward Distribution
- Call `competition.award_rewards()` on ended competitions to distribute rewards
- Point rewards are automatically added to user accounts
- Participants are linked to claimed rewards

## URL Patterns

```python
/competitions/                              # List all competitions
/competitions/<id>/                         # Competition detail
/competitions/<id>/join/                    # Join competition
/competitions/<id>/leaderboard/             # Full leaderboard
```

## Templates

- `web/templates/web/competition_list.html` - Competition listing with filters
- `web/templates/web/competition_detail.html` - Detailed competition view
- `web/templates/web/competition_leaderboard.html` - Full leaderboard table

## Best Practices

1. **Set Clear Dates**: Ensure start_date < end_date
2. **Configure Rewards**: Add rewards before making competition active
3. **Link Challenges**: Add challenges that align with competition goals
4. **Update Status**: Move competitions through lifecycle (upcoming → active → ended)
5. **Award Rewards**: Call award_rewards() method after competition ends

## Example Workflow

```python
# Create a competition
competition = Competition.objects.create(
    title="Python Mastery Challenge",
    description="Complete Python challenges to win prizes",
    start_date=timezone.now(),
    end_date=timezone.now() + timedelta(days=30),
    status="active",
    entry_fee_points=50
)

# Add challenges
competition.challenges.add(challenge1, challenge2, challenge3)

# Add rewards
CompetitionReward.objects.create(
    competition=competition,
    reward_type="scholarship",
    name="$500 Scholarship",
    description="For top performer",
    position=1,
    value=500.00
)

# When competition ends
competition.status = "ended"
competition.save()
competition.award_rewards()  # Distribute rewards to winners
```

## Testing

Comprehensive tests are available in `web/tests/test_competition.py` covering:
- Model creation and validation
- Relationships between models
- Reward type validations
- Participant ranking and scoring
- Competition state management
