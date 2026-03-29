# Share to Unlock Feature

## Overview
The Share to Unlock feature allows teachers to incentivize course promotion by requiring students to share course materials on social media platforms to unlock exclusive bonus content.

## How It Works

### For Teachers
1. When uploading course materials, teachers can mark materials as "unlock by sharing"
2. Teachers can set the number of shares required (1, 2, 3, etc.)
3. Locked materials are visible to students but not accessible until sharing requirement is met
4. Teachers can track which students have unlocked materials via the admin panel

### For Students
1. Enrolled students see locked materials with a lock icon 🔒
2. A "Share to Unlock" button is displayed with share progress (e.g., "Shares: 0/1")
3. Clicking the button generates a unique share link
4. Students share the link on social media (Twitter, Facebook, LinkedIn)
5. After sharing, the system verifies the share and unlocks the material
6. Unlocked materials show an unlock icon 🔓 and are fully accessible

## Features

### Multi-Platform Support
- Twitter
- Facebook
- LinkedIn
- Email
- Other platforms

### Progressive Unlocking
- Materials can require 1 or more shares
- Progress is tracked: "Shares: 1/3" shows student progress
- Each share is verified before unlocking

### Visual Indicators
- **Locked materials**: Orange lock icon with share button
- **Unlocked materials**: Green unlock icon with download/access link
- **Progress tracking**: Shows current shares vs required shares

## Technical Implementation

### Database Models

#### ShareUnlock Model
```python
class ShareUnlock(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="share_unlocks")
    material = models.ForeignKey(CourseMaterial, on_delete=models.CASCADE, related_name="share_unlocks")
    share_token = models.CharField(max_length=32, unique=True)
    shared_at = models.DateTimeField(auto_now_add=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    is_verified = models.BooleanField(default=False)
    platform = models.CharField(max_length=20, choices=[...])
```

#### CourseMaterial Updates
```python
class CourseMaterial(models.Model):
    # ... existing fields ...
    unlock_by_sharing = models.BooleanField(default=False)
    shares_required = models.PositiveIntegerField(default=1)

    def is_unlocked_for_user(self, user):
        if not self.unlock_by_sharing:
            return True
        verified_shares = self.share_unlocks.filter(
            user=user, is_verified=True
        ).count()
        return verified_shares >= self.shares_required
```

### API Endpoints

#### Create Share Token
- **URL**: `/material/<material_id>/create-share-token/`
- **Method**: POST
- **Auth**: Required
- **Response**: JSON with share_token, share_url, share_text

#### Verify Share
- **URL**: `/material/share/<share_token>/`
- **Method**: GET
- **Response**: Redirects to course detail with success message

## Usage Examples

### Example 1: Single Share Unlock
```
Material: "Python Advanced Tips (Bonus)"
unlock_by_sharing: True
shares_required: 1

Student Action: Share once → Material unlocked
```

### Example 2: Multiple Share Unlock
```
Material: "Complete Project Template (Premium)"
unlock_by_sharing: True
shares_required: 3

Student Action: Share 3 times → Material unlocked
Progress shown: "Shares: 0/3" → "Shares: 1/3" → "Shares: 2/3" → Unlocked!
```

## Admin Configuration

### Adding Share-to-Unlock Materials

1. Go to Django Admin → Course Materials
2. Create or edit a material
3. Check "Unlock by sharing"
4. Set "Shares required" (default: 1)
5. Save the material

### Viewing Share Statistics

1. Go to Django Admin → Share Unlocks
2. Filter by material, user, platform, verification status
3. View detailed share history

## Benefits

### For Teachers
- **Increased Visibility**: Courses get promoted organically
- **Student Engagement**: Students motivated to share quality content
- **Analytics**: Track which materials drive the most shares

### For Students
- **Exclusive Content**: Access to bonus materials
- **Social Recognition**: Share achievements with their network
- **No Extra Cost**: Unlock premium content through sharing

## Testing

Comprehensive tests are included in `web/tests/test_share_unlock.py`

## Security

1. **Authentication Required**: Only authenticated users can create share tokens
2. **Enrollment Check**: Users must be enrolled or be the teacher
3. **Unique Tokens**: Each share has a unique 32-character token
4. **CSRF Protection**: All POST requests are CSRF protected
