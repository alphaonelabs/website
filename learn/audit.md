# Migration audit

Last organized: 2026-07-05 21:32:46

This file is now the active migration backlog. Items that were current, platform-replaced, or purposefully omitted were removed from `legacy-site-source` and moved to the completed section below.

## Summary

- Active backlog items: 236
- Completed/removed items: 239
- Keep `MIGRATION.md` as the concise handoff and sign-off checklist.
- Keep `audit.md` for item-level owner decisions and remaining implementation work.

## Active migration backlog

These items remain because they need testing, product decisions, or deeper parity work. Legacy source files for these items were kept when still present so they can be referenced.

### Needs testing / validation

1. `web/tests/__init__.py`
Status: Needs decision
Current comparable: -
Owner note: make sure we have good test coverage
Next step: Needs current Worker/front-end test coverage decision.

2. `web/tests/test_achievements.py`
Status: Needs decision
Current comparable: -
Owner note: make sure we have good test coverage
Next step: Needs current Worker/front-end test coverage decision.

3. `web/tests/test_admin.py`
Status: Needs decision
Current comparable: -
Owner note: make sure we have good test coverage
Next step: Needs current Worker/front-end test coverage decision.

4. `web/tests/test_avatar.py`
Status: Needs decision
Current comparable: -
Owner note: make sure we have good test coverage
Next step: Needs current Worker/front-end test coverage decision.

5. `web/tests/test_calendar.py`
Status: Needs decision
Current comparable: -
Owner note: make sure we have good test coverage
Next step: Needs current Worker/front-end test coverage decision.

6. `web/tests/test_cart.py`
Status: Needs decision
Current comparable: -
Owner note: make sure we have good test coverage
Next step: Needs current Worker/front-end test coverage decision.

7. `web/tests/test_direct_enrollment.py`
Status: Needs decision
Current comparable: -
Owner note: make sure we have good test coverage
Next step: Needs current Worker/front-end test coverage decision.

8. `web/tests/test_discount.py`
Status: Needs decision
Current comparable: -
Owner note: make sure we have good test coverage
Next step: Needs current Worker/front-end test coverage decision.

9. `web/tests/test_donation_views.py`
Status: Needs decision
Current comparable: -
Owner note: make sure we have good test coverage
Next step: Needs current Worker/front-end test coverage decision.

10. `web/tests/test_educationalvideosupload.py`
Status: Needs decision
Current comparable: -
Owner note: make sure we have good test coverage
Next step: Needs current Worker/front-end test coverage decision.

11. `web/tests/test_feature_vote.py`
Status: Needs decision
Current comparable: -
Owner note: make sure we have good test coverage
Next step: Needs current Worker/front-end test coverage decision.

12. `web/tests/test_forms.py`
Status: Needs decision
Current comparable: -
Owner note: make sure we have good test coverage
Next step: Needs current Worker/front-end test coverage decision.

13. `web/tests/test_free_cart_checkout.py`
Status: Needs decision
Current comparable: -
Owner note: make sure we have good test coverage
Next step: Needs current Worker/front-end test coverage decision.

14. `web/tests/test_free_course_enrollment.py`
Status: Needs decision
Current comparable: -
Owner note: make sure we have good test coverage
Next step: Needs current Worker/front-end test coverage decision.

15. `web/tests/test_grade_link_feature.py`
Status: Needs decision
Current comparable: -
Owner note: make sure we have good test coverage
Next step: Needs current Worker/front-end test coverage decision.

16. `web/tests/test_leaderboard.py`
Status: Needs decision
Current comparable: -
Owner note: make sure we have good test coverage
Next step: Needs current Worker/front-end test coverage decision.

17. `web/tests/test_learningstreak.py`
Status: Needs decision
Current comparable: -
Owner note: make sure we have good test coverage
Next step: Needs current Worker/front-end test coverage decision.

18. `web/tests/test_middleware.py`
Status: Needs decision
Current comparable: -
Owner note: make sure we have good test coverage
Next step: Needs current Worker/front-end test coverage decision.

19. `web/tests/test_models.py`
Status: Needs decision
Current comparable: -
Owner note: make sure we have good test coverage
Next step: Needs current Worker/front-end test coverage decision.

20. `web/tests/test_nitter.py`
Status: Needs decision
Current comparable: -
Owner note: make sure we have good test coverage
Next step: Needs current Worker/front-end test coverage decision.

21. `web/tests/test_progress_visualization.py`
Status: Needs decision
Current comparable: -
Owner note: make sure we have good test coverage
Next step: Needs current Worker/front-end test coverage decision.

22. `web/tests/test_public_profile.py`
Status: Needs decision
Current comparable: -
Owner note: make sure we have good test coverage
Next step: Needs current Worker/front-end test coverage decision.

23. `web/tests/test_referrals.py`
Status: Needs decision
Current comparable: -
Owner note: make sure we have good test coverage
Next step: Needs current Worker/front-end test coverage decision.

24. `web/tests/test_securemessaging.py`
Status: Needs decision
Current comparable: -
Owner note: make sure we have good test coverage
Next step: Needs current Worker/front-end test coverage decision.

25. `web/tests/test_send_assignment_reminders.py`
Status: Needs decision
Current comparable: -
Owner note: make sure we have good test coverage
Next step: Needs current Worker/front-end test coverage decision.

26. `web/tests/test_session_waiting_room.py`
Status: Needs decision
Current comparable: -
Owner note: make sure we have good test coverage
Next step: Needs current Worker/front-end test coverage decision.

27. `web/tests/test_signup.py`
Status: Needs decision
Current comparable: -
Owner note: make sure we have good test coverage
Next step: Needs current Worker/front-end test coverage decision.

28. `web/tests/test_study_groups.py`
Status: Needs decision
Current comparable: -
Owner note: make sure we have good test coverage
Next step: Needs current Worker/front-end test coverage decision.

29. `web/tests/test_teach.py`
Status: Needs decision
Current comparable: -
Owner note: make sure we have good test coverage
Next step: Needs current Worker/front-end test coverage decision.

30. `web/tests/test_utils.py`
Status: Needs decision
Current comparable: -
Owner note: make sure we have good test coverage
Next step: Needs current Worker/front-end test coverage decision.

31. `web/tests/test_views.py`
Status: Needs decision
Current comparable: -
Owner note: make sure we have good test coverage
Next step: Needs current Worker/front-end test coverage decision.

32. `web/urls.py`
Status: First-class replacement
Current comparable: `src/worker.py`
Owner note: make sure we have good test coverage
Next step: Needs current Worker/front-end test coverage decision.

33. `web/utils.py`
Status: Needs review
Current comparable: `src/worker.py`
Owner note: make sure we have good test coverage
Next step: Needs current Worker/front-end test coverage decision.

### Needs product decision

1. `static/images/red-dot.png`
Status: Needs asset decision
Current comparable: -
Owner note: not sure
Next step: Needs product/engineering decision before removal.

2. `static/images/yellow-dot.png`
Status: Needs asset decision
Current comparable: -
Owner note: not sure
Next step: Needs product/engineering decision before removal.

3. `web/widgets.py`
Status: Needs review
Current comparable: `src/worker.py`
Owner note: not sure about this make sure we have it if its good
Next step: Needs product/engineering decision before removal.

### Needs implementation or parity review

1. `web/admin_system.py`
Status: Needs review
Current comparable: `src/worker.py`
Owner note: make sure we have everytong this did on the new site
Next step: Needs validation or deeper parity work before legacy reference can be removed.

2. `web/admin_views.py`
Status: First-class replacement
Current comparable: `public/admin.html`
Owner note: move and make sure we have everying
Next step: Needs validation or deeper parity work before legacy reference can be removed.

3. `web/calendar_sync.py`
Status: Likely replacement
Current comparable: `public/calendar.html`
Owner note: make sure we have the matched funcditonality
Next step: Needs validation or deeper parity work before legacy reference can be removed.

4. `web/consumers.py`
Status: Needs review
Current comparable: `src/worker.py`
Owner note: remove it we have DO now make sure we have parity
Next step: Needs validation or deeper parity work before legacy reference can be removed.

5. `web/marketing.py`
Status: Needs review
Current comparable: `src/worker.py`
Owner note: No owner note recorded.
Next step: Needs mapping/review before removal.

6. `web/notifications.py`
Status: Partial replacement
Current comparable: `public/notification-preferences.html`
Owner note: make sure we have all notifications setup and parity
Next step: Needs validation or deeper parity work before legacy reference can be removed.

7. `web/peer_challenge_views.py`
Status: First-class replacement
Current comparable: `public/challenges.html`
Owner note: make sure we have this all setup and working
Next step: Needs validation or deeper parity work before legacy reference can be removed.

8. `web/quiz_views.py`
Status: First-class replacement
Current comparable: `public/quizzes.html`
Owner note: make sure we have this all setup and working
Next step: Needs validation or deeper parity work before legacy reference can be removed.

9. `web/recommendations.py`
Status: Needs review
Current comparable: `src/worker.py`
Owner note: make sure we have this all setup and working
Next step: Needs validation or deeper parity work before legacy reference can be removed.

10. `web/referrals.py`
Status: Likely replacement
Current comparable: `public/referrals.html`
Owner note: make sure we have this all setup and working
Next step: Needs validation or deeper parity work before legacy reference can be removed.

11. `web/routing.py`
Status: Needs review
Current comparable: `src/worker.py`
Owner note: make sure we have this all setup and working
Next step: Needs validation or deeper parity work before legacy reference can be removed.

12. `web/secure_messaging.py`
Status: First-class replacement
Current comparable: `public/messages.html`
Owner note: make sure we have this all setup and working
Next step: Needs validation or deeper parity work before legacy reference can be removed.

13. `web/services/achievement.py`
Status: Needs review
Current comparable: `src/worker.py`
Owner note: make sure we have this all setup and working
Next step: Needs validation or deeper parity work before legacy reference can be removed.

14. `web/settings.py`
Status: Needs review
Current comparable: `src/worker.py`
Owner note: remove make sure we keep everyting we need add notes if we don't have something
Next step: Needs validation or deeper parity work before legacy reference can be removed.

15. `web/slack.py`
Status: Needs review
Current comparable: `src/worker.py`
Owner note: make sure we have this all setup and working
Next step: Needs validation or deeper parity work before legacy reference can be removed.

16. `web/social.py`
Status: Needs review
Current comparable: `src/worker.py`
Owner note: make sure we have this all setup and working
Next step: Needs validation or deeper parity work before legacy reference can be removed.

17. `web/static/images/placeholder.jpg`
Status: Needs asset decision
Current comparable: -
Owner note: make sure we have this all setup and working
Next step: Needs validation or deeper parity work before legacy reference can be removed.

18. `web/static/js/classes_map.js`
Status: Needs asset decision
Current comparable: -
Owner note: make sure we have this all setup and working
Next step: Current classes map exists, but map/location parity still needs functional validation.

19. `web/static/js/progress_visualization.js`
Status: Needs asset decision
Current comparable: -
Owner note: make sure we have this all setup and working
Next step: Copied current asset, but progress visualization integration still needs validation.

20. `web/static/js/surveys.js`
Status: Needs asset decision
Current comparable: -
Owner note: make sure we have this all setup and working
Next step: Copied current asset, but survey authoring/results need deeper rebuild/testing.

21. `web/static/js/vote-utils.js`
Status: Needs asset decision
Current comparable: -
Owner note: make sure we have this all setup and working
Next step: Copied current asset, but feature vote behavior needs validation.

22. `web/templates/account/notification_preferences.html`
Status: Partial replacement
Current comparable: `public/profile.html`
Owner note: make sure we have this all setup and working
Next step: Current notification preferences page/API exists; test preferences end to end.

23. `web/templates/account/signup.html`
Status: Partial replacement
Current comparable: `public/profile.html`
Owner note: make sure we have this all setup and working
Next step: Current login/register flow exists; test registration and verification end to end.

24. `web/templates/add_meme.html`
Status: Needs mapping
Current comparable: -
Owner note: make sure we have this all setup and working
Next step: Needs validation or deeper parity work before legacy reference can be removed.

25. `web/templates/admin/auth/user/change_form.html`
Status: Needs mapping
Current comparable: -
Owner note: make sure we have this all setup and working
Next step: Needs validation or deeper parity work before legacy reference can be removed.

26. `web/templates/admin/dashboard.html`
Status: Likely replacement
Current comparable: `public/dashboard.html`
Owner note: make sure we have this all setup and working
Next step: Needs validation or deeper parity work before legacy reference can be removed.

27. `web/templates/admin/system_dashboard.html`
Status: Needs mapping
Current comparable: -
Owner note: make sure we have this all setup and working
Next step: Needs validation or deeper parity work before legacy reference can be removed.

28. `web/templates/allauth/layouts/base.html`
Status: Needs mapping
Current comparable: -
Owner note: make sure we have this all setup and working
Next step: Needs validation or deeper parity work before legacy reference can be removed.

29. `web/templates/analytics/admin_analytics.html`
Status: Needs mapping
Current comparable: -
Owner note: make sure we have this all setup and working
Next step: Needs validation or deeper parity work before legacy reference can be removed.

30. `web/templates/analytics/analytics_dashboard.html`
Status: Needs mapping
Current comparable: -
Owner note: make sure we have this all setup and working
Next step: Needs validation or deeper parity work before legacy reference can be removed.

31. `web/templates/avatar/customize.html`
Status: Needs mapping
Current comparable: -
Owner note: make sure we have this all setup and working
Next step: Needs validation or deeper parity work before legacy reference can be removed.

32. `web/templates/award_achievement.html`
Status: Needs mapping
Current comparable: -
Owner note: make sure we have this all setup and working
Next step: Needs validation or deeper parity work before legacy reference can be removed.

33. `web/templates/blog/create.html`
Status: First-class replacement
Current comparable: `public/blog.html`
Owner note: make sure we have this all setup and working
Next step: Needs validation or deeper parity work before legacy reference can be removed.

34. `web/templates/blog/detail.html`
Status: First-class replacement
Current comparable: `public/blog.html`
Owner note: make sure we have this all setup and working
Next step: Needs validation or deeper parity work before legacy reference can be removed.

35. `web/templates/blog/list.html`
Status: First-class replacement
Current comparable: `public/blog.html`
Owner note: make sure we have this all setup and working
Next step: Needs validation or deeper parity work before legacy reference can be removed.

36. `web/templates/calendar/create.html`
Status: First-class replacement
Current comparable: `public/calendar.html`
Owner note: make sure we have this all setup and working
Next step: Needs validation or deeper parity work before legacy reference can be removed.

37. `web/templates/calendar/view.html`
Status: First-class replacement
Current comparable: `public/calendar.html`
Owner note: make sure we have this all setup and working
Next step: Needs validation or deeper parity work before legacy reference can be removed.

38. `web/templates/cart/cart.html`
Status: First-class replacement
Current comparable: `public/cart.html`
Owner note: make sure we have this all setup and working
Next step: Current cart exists; test anonymous cart, logged-in cart, and checkout.

39. `web/templates/cart/receipt.html`
Status: Partial replacement
Current comparable: `public/cart.html`
Owner note: make sure we have this all setup and working
Next step: Checkout success exists; test post-payment receipt/completion behavior.

40. `web/templates/checkout.html`
Status: Needs mapping
Current comparable: -
Owner note: make sure we have this all setup and working
Next step: Checkout API exists; test Stripe guest and logged-in checkout.

41. `web/templates/courses/add_review.html`
Status: Partial replacement
Current comparable: `public/activity.html`
Owner note: make sure we have this all setup and working
Next step: Needs validation or deeper parity work before legacy reference can be removed.

42. `web/templates/courses/add_student.html`
Status: Partial replacement
Current comparable: `public/activity.html`
Owner note: make sure we have this all setup and working
Next step: Needs validation or deeper parity work before legacy reference can be removed.

43. `web/templates/courses/calendar_links.html`
Status: Partial replacement
Current comparable: `public/activity.html`
Owner note: make sure we have this all setup and working
Next step: Needs validation or deeper parity work before legacy reference can be removed.

44. `web/templates/courses/certificate_detail.html`
Status: Partial replacement
Current comparable: `public/activity.html`
Owner note: make sure we have this all setup and working
Next step: Needs validation or deeper parity work before legacy reference can be removed.

45. `web/templates/courses/create.html`
Status: Partial replacement
Current comparable: `public/activity.html`
Owner note: make sure we have this all setup and working
Next step: Needs validation or deeper parity work before legacy reference can be removed.

46. `web/templates/courses/delete_confirm.html`
Status: Partial replacement
Current comparable: `public/activity.html`
Owner note: make sure we have this all setup and working
Next step: Needs validation or deeper parity work before legacy reference can be removed.

47. `web/templates/courses/delete_material_confirm.html`
Status: Partial replacement
Current comparable: `public/activity.html`
Owner note: make sure we have this all setup and working
Next step: Needs validation or deeper parity work before legacy reference can be removed.

48. `web/templates/courses/detail.html`
Status: First-class replacement
Current comparable: `public/activity.html`
Owner note: make sure we have this all setup and working
Next step: Needs validation or deeper parity work before legacy reference can be removed.

49. `web/templates/courses/edit_or_add_review.html`
Status: Partial replacement
Current comparable: `public/activity.html`
Owner note: make sure we have this all setup and working
Next step: Needs validation or deeper parity work before legacy reference can be removed.

50. `web/templates/courses/invite.html`
Status: Partial replacement
Current comparable: `public/activity.html`
Owner note: make sure we have this all setup and working
Next step: Needs validation or deeper parity work before legacy reference can be removed.

51. `web/templates/courses/mark_attendance.html`
Status: Partial replacement
Current comparable: `public/activity.html`
Owner note: make sure we have this all setup and working
Next step: Needs validation or deeper parity work before legacy reference can be removed.

52. `web/templates/courses/marketing.html`
Status: Partial replacement
Current comparable: `public/activity.html`
Owner note: make sure we have this all setup and working
Next step: Needs validation or deeper parity work before legacy reference can be removed.

53. `web/templates/courses/message_students.html`
Status: Partial replacement
Current comparable: `public/activity.html`
Owner note: make sure we have this all setup and working
Next step: Needs validation or deeper parity work before legacy reference can be removed.

54. `web/templates/courses/message_teacher.html`
Status: Partial replacement
Current comparable: `public/activity.html`
Owner note: make sure we have this all setup and working
Next step: Needs validation or deeper parity work before legacy reference can be removed.

55. `web/templates/courses/payment.html`
Status: Partial replacement
Current comparable: `public/activity.html`
Owner note: make sure we have this all setup and working
Next step: Needs validation or deeper parity work before legacy reference can be removed.

56. `web/templates/courses/progress_overview.html`
Status: Partial replacement
Current comparable: `public/activity.html`
Owner note: make sure we have this all setup and working
Next step: Needs validation or deeper parity work before legacy reference can be removed.

57. `web/templates/courses/progress_visualization.html`
Status: Partial replacement
Current comparable: `public/activity.html`
Owner note: make sure we have this all setup and working
Next step: Needs validation or deeper parity work before legacy reference can be removed.

58. `web/templates/courses/search.html`
Status: First-class replacement
Current comparable: `public/search.html`
Owner note: make sure we have this all setup and working
Next step: Needs validation or deeper parity work before legacy reference can be removed.

59. `web/templates/courses/session_form.html`
Status: Partial replacement
Current comparable: `public/activity.html`
Owner note: make sure we have this all setup and working
Next step: Needs validation or deeper parity work before legacy reference can be removed.

60. `web/templates/courses/student_management.html`
Status: Partial replacement
Current comparable: `public/activity.html`
Owner note: make sure we have this all setup and working
Next step: Needs validation or deeper parity work before legacy reference can be removed.

61. `web/templates/courses/student_progress.html`
Status: Partial replacement
Current comparable: `public/activity.html`
Owner note: make sure we have this all setup and working
Next step: Needs validation or deeper parity work before legacy reference can be removed.

62. `web/templates/courses/update.html`
Status: Partial replacement
Current comparable: `public/activity.html`
Owner note: make sure we have this all setup and working
Next step: Needs validation or deeper parity work before legacy reference can be removed.

63. `web/templates/courses/upload_material.html`
Status: Partial replacement
Current comparable: `public/activity.html`
Owner note: make sure we have this all setup and working
Next step: Needs validation or deeper parity work before legacy reference can be removed.

64. `web/templates/dashboard/student.html`
Status: Partial replacement
Current comparable: `public/dashboard.html`
Owner note: make sure we have this all setup and working
Next step: Needs validation or deeper parity work before legacy reference can be removed.

65. `web/templates/dashboard/teacher.html`
Status: Partial replacement
Current comparable: `public/dashboard.html`
Owner note: make sure we have this all setup and working
Next step: Needs validation or deeper parity work before legacy reference can be removed.

66. `web/templates/donate.html`
Status: First-class replacement
Current comparable: `public/donate.html`
Owner note: make sure we have this all setup and working
Next step: Needs validation or deeper parity work before legacy reference can be removed.

67. `web/templates/donation_success.html`
Status: Needs mapping
Current comparable: -
Owner note: make sure we have this all setup and working
Next step: Donation checkout exists; confirm success state and donor email behavior.

68. `web/templates/emails/assignment_reminder.html`
Status: Needs mapping
Current comparable: -
Owner note: make sure we have this all setup and working
Next step: Needs validation or deeper parity work before legacy reference can be removed.

69. `web/templates/emails/base_email.html`
Status: Needs mapping
Current comparable: -
Owner note: make sure we have this all setup and working
Next step: Needs validation or deeper parity work before legacy reference can be removed.

70. `web/templates/emails/course_invitation.html`
Status: Needs mapping
Current comparable: -
Owner note: make sure we have this all setup and working
Next step: Needs validation or deeper parity work before legacy reference can be removed.

71. `web/templates/emails/course_update.html`
Status: Needs mapping
Current comparable: -
Owner note: make sure we have this all setup and working
Next step: Needs validation or deeper parity work before legacy reference can be removed.

72. `web/templates/emails/donation_thank_you.html`
Status: Needs mapping
Current comparable: -
Owner note: make sure we have this all setup and working
Next step: Needs validation or deeper parity work before legacy reference can be removed.

73. `web/templates/emails/enrollment_confirmation.html`
Status: Needs mapping
Current comparable: -
Owner note: make sure we have this all setup and working
Next step: Needs validation or deeper parity work before legacy reference can be removed.

74. `web/templates/emails/learn_interest.html`
Status: Needs mapping
Current comparable: -
Owner note: make sure we have this all setup and working
Next step: Needs validation or deeper parity work before legacy reference can be removed.

75. `web/templates/emails/marketing/course_promotion.html`
Status: Needs mapping
Current comparable: -
Owner note: make sure we have this all setup and working
Next step: Needs validation or deeper parity work before legacy reference can be removed.

76. `web/templates/emails/marketing/course_promotion.txt`
Status: Needs mapping
Current comparable: -
Owner note: make sure we have this all setup and working
Next step: Needs validation or deeper parity work before legacy reference can be removed.

77. `web/templates/emails/new_enrollment_notification.html`
Status: Needs mapping
Current comparable: -
Owner note: make sure we have this all setup and working
Next step: Needs validation or deeper parity work before legacy reference can be removed.

78. `web/templates/emails/notification.html`
Status: Needs mapping
Current comparable: -
Owner note: make sure we have this all setup and working
Next step: Needs validation or deeper parity work before legacy reference can be removed.

79. `web/templates/emails/session_reminder.html`
Status: Needs mapping
Current comparable: -
Owner note: make sure we have this all setup and working
Next step: Needs validation or deeper parity work before legacy reference can be removed.

80. `web/templates/emails/student_enrollment.html`
Status: Needs mapping
Current comparable: -
Owner note: make sure we have this all setup and working
Next step: Needs validation or deeper parity work before legacy reference can be removed.

81. `web/templates/emails/teach_application.html`
Status: Needs mapping
Current comparable: -
Owner note: make sure we have this all setup and working
Next step: Needs validation or deeper parity work before legacy reference can be removed.

82. `web/templates/emails/teacher_message.html`
Status: Needs mapping
Current comparable: -
Owner note: make sure we have this all setup and working
Next step: Needs validation or deeper parity work before legacy reference can be removed.

83. `web/templates/emails/verification_reminder.html`
Status: Needs mapping
Current comparable: -
Owner note: make sure we have this all setup and working
Next step: Needs validation or deeper parity work before legacy reference can be removed.

84. `web/templates/emails/waiting_room_fulfilled.html`
Status: Needs mapping
Current comparable: -
Owner note: make sure we have this all setup and working
Next step: Needs validation or deeper parity work before legacy reference can be removed.

85. `web/templates/emails/waiting_room_join_teacher.html`
Status: Needs mapping
Current comparable: -
Owner note: make sure we have this all setup and working
Next step: Needs validation or deeper parity work before legacy reference can be removed.

86. `web/templates/emails/weekly_progress.html`
Status: Needs mapping
Current comparable: -
Owner note: make sure we have this all setup and working
Next step: Needs validation or deeper parity work before legacy reference can be removed.

87. `web/templates/emails/welcome_guest.html`
Status: Needs mapping
Current comparable: -
Owner note: make sure we have this all setup and working
Next step: Needs validation or deeper parity work before legacy reference can be removed.

88. `web/templates/emails/welcome_guest.txt`
Status: Needs mapping
Current comparable: -
Owner note: make sure we have this all setup and working
Next step: Needs validation or deeper parity work before legacy reference can be removed.

89. `web/templates/emails/welcome_teach_course.html`
Status: Needs mapping
Current comparable: -
Owner note: make sure we have this all setup and working
Next step: Needs validation or deeper parity work before legacy reference can be removed.

90. `web/templates/emails/welcome_teach_course.txt`
Status: Needs mapping
Current comparable: -
Owner note: make sure we have this all setup and working
Next step: Needs validation or deeper parity work before legacy reference can be removed.

91. `web/templates/features.html`
Status: Likely replacement
Current comparable: `public/features.html`
Owner note: make sure we have this all setup and working
Next step: Needs validation or deeper parity work before legacy reference can be removed.

92. `web/templates/feedback.html`
Status: Likely replacement
Current comparable: `public/feedback.html`
Owner note: make sure we have this all setup and working
Next step: Needs validation or deeper parity work before legacy reference can be removed.

93. `web/templates/forum/categories.html`
Status: First-class replacement
Current comparable: `public/forum.html`
Owner note: make sure we have this all setup and working
Next step: Needs validation or deeper parity work before legacy reference can be removed.

94. `web/templates/grade_links/grade_link.html`
Status: First-class replacement
Current comparable: `public/grade-links.html`
Owner note: make sure we have this all setup and working
Next step: Needs validation or deeper parity work before legacy reference can be removed.

95. `web/templates/grade_links/link_detail.html`
Status: First-class replacement
Current comparable: `public/grade-links.html`
Owner note: make sure we have this all setup and working
Next step: Needs validation or deeper parity work before legacy reference can be removed.

96. `web/templates/grade_links/link_list.html`
Status: First-class replacement
Current comparable: `public/grade-links.html`
Owner note: make sure we have this all setup and working
Next step: Needs validation or deeper parity work before legacy reference can be removed.

97. `web/templates/grade_links/submit_link.html`
Status: First-class replacement
Current comparable: `public/grade-links.html`
Owner note: make sure we have this all setup and working
Next step: Needs validation or deeper parity work before legacy reference can be removed.

98. `web/templates/graphing_calculator.html`
Status: First-class replacement
Current comparable: `public/calculator.html`
Owner note: make sure we have this all setup and working
Next step: Needs validation or deeper parity work before legacy reference can be removed.

99. `web/templates/includes/logged_in_as_banner.html`
Status: Needs mapping
Current comparable: -
Owner note: make sure we have this all setup and working
Next step: Needs validation or deeper parity work before legacy reference can be removed.

100. `web/templates/index.html`
Status: First-class replacement
Current comparable: `public/index.html`
Owner note: make sure we have this all setup and working
Next step: Homepage is current; verify server-rendered featured classes and GSOC CTA visually.

101. `web/templates/learn.html`
Status: Needs mapping
Current comparable: -
Owner note: make sure we have this all setup and working
Next step: Needs validation or deeper parity work before legacy reference can be removed.

102. `web/templates/membership_checkout.html`
Status: Needs mapping
Current comparable: -
Owner note: make sure we have this all setup and working
Next step: Needs validation or deeper parity work before legacy reference can be removed.

103. `web/templates/membership_settings.html`
Status: Needs mapping
Current comparable: -
Owner note: make sure we have this all setup and working
Next step: Needs validation or deeper parity work before legacy reference can be removed.

104. `web/templates/membership_success.html`
Status: Needs mapping
Current comparable: -
Owner note: make sure we have this all setup and working
Next step: Needs validation or deeper parity work before legacy reference can be removed.

105. `web/templates/meme_detail.html`
Status: Needs mapping
Current comparable: -
Owner note: make sure we have this all setup and working
Next step: Needs validation or deeper parity work before legacy reference can be removed.

106. `web/templates/memes.html`
Status: First-class replacement
Current comparable: `public/memes.html`
Owner note: make sure we have this all setup and working
Next step: Needs validation or deeper parity work before legacy reference can be removed.

107. `web/templates/orders/order_detail.html`
Status: Needs mapping
Current comparable: -
Owner note: make sure we have this all setup and working
Next step: Needs validation or deeper parity work before legacy reference can be removed.

108. `web/templates/orders/order_management.html`
Status: Needs mapping
Current comparable: -
Owner note: make sure we have this all setup and working
Next step: Needs validation or deeper parity work before legacy reference can be removed.

109. `web/templates/profile.html`
Status: First-class replacement
Current comparable: `public/profile.html`
Owner note: make sure we have this all setup and working
Next step: Current profile exists; test profile update and account deletion.

110. `web/templates/public_profile_detail.html`
Status: Needs mapping
Current comparable: -
Owner note: make sure we have this all setup and working
Next step: Needs validation or deeper parity work before legacy reference can be removed.

111. `web/templates/sitemap.html`
Status: Likely replacement
Current comparable: `public/sitemap.html`
Owner note: make sure we have this all setup and working
Next step: Needs validation or deeper parity work before legacy reference can be removed.

112. `web/templates/social_media_dashboard.html`
Status: Needs mapping
Current comparable: -
Owner note: make sure we have this all setup and working
Next step: Needs validation or deeper parity work before legacy reference can be removed.

113. `web/templates/status.html`
Status: Likely replacement
Current comparable: `public/status.html`
Owner note: make sure we have this all setup and working
Next step: Needs validation or deeper parity work before legacy reference can be removed.

114. `web/templates/streak_detail.html`
Status: Needs mapping
Current comparable: -
Owner note: make sure we have this all setup and working
Next step: Needs validation or deeper parity work before legacy reference can be removed.

115. `web/templates/subjects.html`
Status: Needs mapping
Current comparable: -
Owner note: make sure we have this all setup and working
Next step: Needs validation or deeper parity work before legacy reference can be removed.

116. `web/templates/success_stories/create.html`
Status: First-class replacement
Current comparable: `public/success-stories.html`
Owner note: make sure we have this all setup and working
Next step: Needs validation or deeper parity work before legacy reference can be removed.

117. `web/templates/success_stories/delete_confirm.html`
Status: First-class replacement
Current comparable: `public/success-stories.html`
Owner note: make sure we have this all setup and working
Next step: Needs validation or deeper parity work before legacy reference can be removed.

118. `web/templates/success_stories/detail.html`
Status: First-class replacement
Current comparable: `public/success-stories.html`
Owner note: make sure we have this all setup and working
Next step: Needs validation or deeper parity work before legacy reference can be removed.

119. `web/templates/success_stories/list.html`
Status: First-class replacement
Current comparable: `public/success-stories.html`
Owner note: make sure we have this all setup and working
Next step: Needs validation or deeper parity work before legacy reference can be removed.

120. `web/templates/surveys/create.html`
Status: First-class replacement
Current comparable: `public/surveys.html`
Owner note: make sure we have this all setup and working
Next step: Needs validation or deeper parity work before legacy reference can be removed.

121. `web/templates/surveys/delete.html`
Status: First-class replacement
Current comparable: `public/surveys.html`
Owner note: make sure we have this all setup and working
Next step: Needs validation or deeper parity work before legacy reference can be removed.

122. `web/templates/surveys/detail.html`
Status: First-class replacement
Current comparable: `public/surveys.html`
Owner note: make sure we have this all setup and working
Next step: Needs validation or deeper parity work before legacy reference can be removed.

123. `web/templates/surveys/list.html`
Status: First-class replacement
Current comparable: `public/surveys.html`
Owner note: make sure we have this all setup and working
Next step: Needs validation or deeper parity work before legacy reference can be removed.

124. `web/templates/surveys/results.html`
Status: First-class replacement
Current comparable: `public/surveys.html`
Owner note: make sure we have this all setup and working
Next step: Needs validation or deeper parity work before legacy reference can be removed.

125. `web/templates/teach.html`
Status: First-class replacement
Current comparable: `public/teach.html`
Owner note: make sure we have this all setup and working
Next step: Needs validation or deeper parity work before legacy reference can be removed.

126. `web/templates/trackers/detail.html`
Status: Needs mapping
Current comparable: -
Owner note: keep tracker stuff
Next step: Owner asked to keep this functionality/reference until parity is confirmed.

127. `web/templates/trackers/embed.html`
Status: Needs mapping
Current comparable: -
Owner note: No owner note recorded.
Next step: Needs mapping/review before removal.

128. `web/templates/trackers/form.html`
Status: Needs mapping
Current comparable: -
Owner note: No owner note recorded.
Next step: Needs mapping/review before removal.

129. `web/templates/trackers/list.html`
Status: Needs mapping
Current comparable: -
Owner note: make sure we have this all setup and working
Next step: Needs validation or deeper parity work before legacy reference can be removed.

130. `web/templates/update_payment_method.html`
Status: Needs mapping
Current comparable: -
Owner note: make sure we have this all setup and working
Next step: Needs validation or deeper parity work before legacy reference can be removed.

131. `web/templates/users_list.html`
Status: Needs mapping
Current comparable: -
Owner note: make sure we have this all setup and working thsi is for the classroom detail I thik
Next step: Needs validation or deeper parity work before legacy reference can be removed.

132. `web/templates/virtual_classroom/attendance.html`
Status: Needs mapping
Current comparable: -
Owner note: keep virtual classroom stuff make sure it works with the new one
Next step: Needs validation or deeper parity work before legacy reference can be removed.

133. `web/templates/virtual_classroom/base.html`
Status: Needs mapping
Current comparable: -
Owner note: keep virtual classroom stuff make sure it works with the new one
Next step: Needs validation or deeper parity work before legacy reference can be removed.

134. `web/templates/virtual_classroom/blackboard.html`
Status: Needs mapping
Current comparable: -
Owner note: keep virtual classroom stuff make sure it works with the new one
Next step: Needs validation or deeper parity work before legacy reference can be removed.

135. `web/templates/virtual_classroom/create.html`
Status: Needs mapping
Current comparable: -
Owner note: keep virtual classroom stuff make sure it works with the new one
Next step: Needs validation or deeper parity work before legacy reference can be removed.

136. `web/templates/virtual_classroom/customize.html`
Status: Needs mapping
Current comparable: -
Owner note: keep virtual classroom stuff make sure it works with the new one
Next step: Needs validation or deeper parity work before legacy reference can be removed.

137. `web/templates/virtual_classroom/delete.html`
Status: Needs mapping
Current comparable: -
Owner note: keep virtual classroom stuff make sure it works with the new one
Next step: Needs validation or deeper parity work before legacy reference can be removed.

138. `web/templates/virtual_classroom/edit.html`
Status: Needs mapping
Current comparable: -
Owner note: keep virtual classroom stuff make sure it works with the new one
Next step: Needs validation or deeper parity work before legacy reference can be removed.

139. `web/templates/virtual_classroom/index.html`
Status: Likely replacement
Current comparable: `public/index.html`
Owner note: keep virtual classroom stuff make sure it works with the new one
Next step: Current virtual classroom exists; test anonymous view and logged-in interaction.

140. `web/templates/virtual_classroom/list.html`
Status: Needs mapping
Current comparable: -
Owner note: keep virtual classroom stuff make sure it works with the new one
Next step: Needs validation or deeper parity work before legacy reference can be removed.

141. `web/templates/virtual_classroom/live_whiteboard.html`
Status: Needs mapping
Current comparable: -
Owner note: keep virtual classroom stuff make sure it works with the new one
Next step: Needs validation or deeper parity work before legacy reference can be removed.

142. `web/templates/virtual_classroom/student_desk.html`
Status: Needs mapping
Current comparable: -
Owner note: keep virtual classroom stuff make sure it works with the new one
Next step: Needs validation or deeper parity work before legacy reference can be removed.

143. `web/templates/virtual_classroom/teacher_resources.html`
Status: Needs mapping
Current comparable: -
Owner note: keep virtual classroom stuff make sure it works with the new one
Next step: Needs validation or deeper parity work before legacy reference can be removed.

144. `web/templates/waiting_room/confirm_delete.html`
Status: Needs mapping
Current comparable: -
Owner note: all activities can have a waiting room now so this can be managed automatically
Next step: Needs mapping/review before removal.

145. `web/templates/waiting_room/create.html`
Status: Needs mapping
Current comparable: -
Owner note: all activities can have a waiting room now so this can be managed automatically
Next step: Needs mapping/review before removal.

146. `web/templates/waiting_room/create_course.html`
Status: Needs mapping
Current comparable: -
Owner note: all activities can have a waiting room now so this can be managed automatically
Next step: Needs mapping/review before removal.

147. `web/templates/waiting_room/detail.html`
Status: Needs mapping
Current comparable: -
Owner note: all activities can have a waiting room now so this can be managed automatically
Next step: Needs mapping/review before removal.

148. `web/templates/waiting_room/list.html`
Status: Needs mapping
Current comparable: -
Owner note: all activities can have a waiting room now so this can be managed automatically
Next step: Needs mapping/review before removal.

149. `web/templates/waiting_room/room_card.html`
Status: Needs mapping
Current comparable: -
Owner note: all activities can have a waiting room now so this can be managed automatically
Next step: Needs mapping/review before removal.

150. `web/templates/web/challenge_detail.html`
Status: Needs mapping
Current comparable: -
Owner note: make sure we have this all setup and working
Next step: Needs validation or deeper parity work before legacy reference can be removed.

151. `web/templates/web/challenge_submit.html`
Status: Needs mapping
Current comparable: -
Owner note: make sure we have this all setup and working
Next step: Needs validation or deeper parity work before legacy reference can be removed.

152. `web/templates/web/classes_map.html`
Status: Likely replacement
Current comparable: `public/classes-map.html`
Owner note: make sure we have this all setup and working
Next step: Needs validation or deeper parity work before legacy reference can be removed.

153. `web/templates/web/current_weekly_challenge.html`
Status: Needs mapping
Current comparable: -
Owner note: keep this make sure its working
Next step: Needs validation or deeper parity work before legacy reference can be removed.

154. `web/templates/web/dashboard/content_status.html`
Status: Needs mapping
Current comparable: -
Owner note: keep this make sure its working
Next step: Needs validation or deeper parity work before legacy reference can be removed.

155. `web/templates/web/emails/teacher_message.html`
Status: Needs mapping
Current comparable: -
Owner note: keep this make sure its working
Next step: Needs validation or deeper parity work before legacy reference can be removed.

156. `web/templates/web/forum/categories.html`
Status: Needs mapping
Current comparable: -
Owner note: keep this make sure its working
Next step: Needs validation or deeper parity work before legacy reference can be removed.

157. `web/templates/web/forum/category.html`
Status: Needs mapping
Current comparable: -
Owner note: keep this make sure its working
Next step: Needs validation or deeper parity work before legacy reference can be removed.

158. `web/templates/web/forum/create_category.html`
Status: Needs mapping
Current comparable: -
Owner note: keep this make sure its working
Next step: Needs validation or deeper parity work before legacy reference can be removed.

159. `web/templates/web/forum/create_topic.html`
Status: Needs mapping
Current comparable: -
Owner note: keep this make sure its working
Next step: Needs validation or deeper parity work before legacy reference can be removed.

160. `web/templates/web/forum/edit_reply.html`
Status: Needs mapping
Current comparable: -
Owner note: keep this make sure its working
Next step: Needs validation or deeper parity work before legacy reference can be removed.

161. `web/templates/web/forum/edit_topic.html`
Status: Needs mapping
Current comparable: -
Owner note: keep this make sure its working
Next step: Needs validation or deeper parity work before legacy reference can be removed.

162. `web/templates/web/forum/my_replies.html`
Status: Needs mapping
Current comparable: -
Owner note: keep this make sure its working
Next step: Needs validation or deeper parity work before legacy reference can be removed.

163. `web/templates/web/forum/my_topics.html`
Status: Needs mapping
Current comparable: -
Owner note: keep this make sure its working
Next step: Needs validation or deeper parity work before legacy reference can be removed.

164. `web/templates/web/forum/topic.html`
Status: Needs mapping
Current comparable: -
Owner note: keep this make sure its working
Next step: Needs validation or deeper parity work before legacy reference can be removed.

165. `web/templates/web/message_teacher.html`
Status: Needs mapping
Current comparable: -
Owner note: keep this make sure its working
Next step: Needs validation or deeper parity work before legacy reference can be removed.

166. `web/templates/web/messaging/compose.html`
Status: Needs mapping
Current comparable: -
Owner note: keep this make sure its working
Next step: Needs validation or deeper parity work before legacy reference can be removed.

167. `web/templates/web/messaging/dashboard.html`
Status: Likely replacement
Current comparable: `public/dashboard.html`
Owner note: keep this make sure its working
Next step: Needs validation or deeper parity work before legacy reference can be removed.

168. `web/templates/web/peer/connections.html`
Status: Needs mapping
Current comparable: -
Owner note: keep this make sure its working
Next step: Needs validation or deeper parity work before legacy reference can be removed.

169. `web/templates/web/peer/inbox.html`
Status: Needs mapping
Current comparable: -
Owner note: keep this make sure its working
Next step: Needs validation or deeper parity work before legacy reference can be removed.

170. `web/templates/web/peer/messages.html`
Status: Likely replacement
Current comparable: `public/messages.html`
Owner note: keep this make sure its working
Next step: Needs validation or deeper parity work before legacy reference can be removed.

171. `web/templates/web/peer_challenges/challenge_list.html`
Status: Needs mapping
Current comparable: -
Owner note: keep this make sure its working
Next step: Needs validation or deeper parity work before legacy reference can be removed.

172. `web/templates/web/peer_challenges/create_challenge.html`
Status: Needs mapping
Current comparable: -
Owner note: keep this make sure its working
Next step: Needs validation or deeper parity work before legacy reference can be removed.

173. `web/templates/web/quiz/add_question.html`
Status: Needs mapping
Current comparable: -
Owner note: keep quiz system make sure it all works
Next step: Needs validation or deeper parity work before legacy reference can be removed.

174. `web/templates/web/quiz/all_attempts.html`
Status: Needs mapping
Current comparable: -
Owner note: keep quiz system make sure it all works
Next step: Needs validation or deeper parity work before legacy reference can be removed.

175. `web/templates/web/quiz/create_quiz.html`
Status: Needs mapping
Current comparable: -
Owner note: keep quiz system make sure it all works
Next step: Needs validation or deeper parity work before legacy reference can be removed.

176. `web/templates/web/quiz/grade_quiz.html`
Status: Needs mapping
Current comparable: -
Owner note: keep quiz system make sure it all works
Next step: Needs validation or deeper parity work before legacy reference can be removed.

177. `web/templates/web/quiz/question_form.html`
Status: Needs mapping
Current comparable: -
Owner note: keep quiz system make sure it all works
Next step: Needs validation or deeper parity work before legacy reference can be removed.

178. `web/templates/web/quiz/quiz_analytics.html`
Status: Needs mapping
Current comparable: -
Owner note: keep quiz system make sure it all works
Next step: Needs validation or deeper parity work before legacy reference can be removed.

179. `web/templates/web/quiz/quiz_detail.html`
Status: Needs mapping
Current comparable: -
Owner note: keep quiz system make sure it all works
Next step: Needs validation or deeper parity work before legacy reference can be removed.

180. `web/templates/web/quiz/quiz_form.html`
Status: Needs mapping
Current comparable: -
Owner note: keep quiz system make sure it all works
Next step: Needs validation or deeper parity work before legacy reference can be removed.

181. `web/templates/web/quiz/quiz_list.html`
Status: Needs mapping
Current comparable: -
Owner note: keep quiz system make sure it all works
Next step: Needs validation or deeper parity work before legacy reference can be removed.

182. `web/templates/web/quiz/quiz_results.html`
Status: Needs mapping
Current comparable: -
Owner note: keep quiz system make sure it all works
Next step: Needs validation or deeper parity work before legacy reference can be removed.

183. `web/templates/web/quiz/take_quiz.html`
Status: Needs mapping
Current comparable: -
Owner note: keep quiz system make sure it all works
Next step: Needs validation or deeper parity work before legacy reference can be removed.

184. `web/templates/web/study/all_groups.html`
Status: Needs mapping
Current comparable: -
Owner note: keep study group functionality it shoudl be an activity type and have these tools around it
Next step: Owner asked to keep this functionality/reference until parity is confirmed.

185. `web/templates/web/study/create_group.html`
Status: Needs mapping
Current comparable: -
Owner note: keep study group functionality it shoudl be an activity type and have these tools around it
Next step: Owner asked to keep this functionality/reference until parity is confirmed.

186. `web/templates/web/study/group_detail.html`
Status: Needs mapping
Current comparable: -
Owner note: keep study group functionality it shoudl be an activity type and have these tools around it
Next step: Owner asked to keep this functionality/reference until parity is confirmed.

187. `web/templates/web/study/groups.html`
Status: Needs mapping
Current comparable: -
Owner note: keep study group functionality it shoudl be an activity type and have these tools around it
Next step: Owner asked to keep this functionality/reference until parity is confirmed.

188. `web/templates/web/study/invitations.html`
Status: Needs mapping
Current comparable: -
Owner note: keep study group functionality it shoudl be an activity type and have these tools around it
Next step: Owner asked to keep this functionality/reference until parity is confirmed.

189. `web/templates/web/study/session_detail.html`
Status: Needs mapping
Current comparable: -
Owner note: keep study group functionality it shoudl be an activity type and have these tools around it
Next step: Owner asked to keep this functionality/reference until parity is confirmed.

190. `web/templates/whiteboard.html`
Status: First-class replacement
Current comparable: `public/whiteboard.html`
Owner note: keep the whieboard and make sure its interactive through the virtual classroom
Next step: Current whiteboard exists; test classroom Durable Object interaction.

191. `web/templatetags/cart_tags.py`
Status: Likely replacement
Current comparable: `public/cart.html`
Owner note: make sure cart is working
Next step: Needs validation or deeper parity work before legacy reference can be removed.

192. `web/templatetags/challenges_extras.py`
Status: Likely replacement
Current comparable: `public/challenges.html`
Owner note: make sure its functioniong
Next step: Needs validation or deeper parity work before legacy reference can be removed.

193. `web/templatetags/dict_filters.py`
Status: Needs review
Current comparable: `src/worker.py`
Owner note: make sure its functioniong
Next step: Needs validation or deeper parity work before legacy reference can be removed.

194. `web/templatetags/markdown_filters.py`
Status: Needs review
Current comparable: `src/worker.py`
Owner note: make sure its functioniong
Next step: Needs validation or deeper parity work before legacy reference can be removed.

195. `web/templatetags/session_filters.py`
Status: Needs review
Current comparable: `src/worker.py`
Owner note: make sure its functioniong
Next step: Needs validation or deeper parity work before legacy reference can be removed.

196. `web/templatetags/string_filters.py`
Status: Needs review
Current comparable: `src/worker.py`
Owner note: make sure its functioniong
Next step: Needs validation or deeper parity work before legacy reference can be removed.

197. `web/video_conferencing.py`
Status: Needs review
Current comparable: `src/worker.py`
Owner note: make sure we have this working
Next step: Needs validation or deeper parity work before legacy reference can be removed.

198. `web/views.py`
Status: First-class replacement
Current comparable: `src/worker.py`
Owner note: make sure we have this working
Next step: Needs validation or deeper parity work before legacy reference can be removed.

199. `web/views_avatar.py`
Status: Partial replacement
Current comparable: `public/profile.html`
Owner note: make sure we have this working
Next step: Needs validation or deeper parity work before legacy reference can be removed.

200. `web/views_whiteboard.py`
Status: First-class replacement
Current comparable: `public/whiteboard.html`
Owner note: make sure we have this working
Next step: Needs validation or deeper parity work before legacy reference can be removed.

## Completed and removed from legacy-site-source

These items no longer need to stay in `legacy-site-source`. They were either migrated into the current Worker/public site, intentionally omitted, or removed because the old platform/runtime no longer applies.

1. `.dockerignore`
Status: Likely replacement
Current comparable: `_django_ref/education-website/.dockerignore`
Owner note: lets not have anything docker related - remove anything related to docker from the project and legacy site source
Next step: Done: Legacy runtime/deployment/reference artifact removed from current migration scope. Source status: already absent from legacy-site-source.

2. `.flake8`
Status: Likely replacement
Current comparable: `_django_ref/education-website/.flake8`
Owner note: sure we can keep this transfer it over
Next step: Done: Moved lint config into current project. Source status: removed from legacy-site-source.

3. `.gitattributes`
Status: Likely replacement
Current comparable: `_django_ref/education-website/.gitattributes`
Owner note: remove this
Next step: Done: Legacy runtime/deployment/reference artifact removed from current migration scope. Source status: already absent from legacy-site-source.

4. `.github/PULL_REQUEST_TEMPLATE.md`
Status: Likely replacement
Current comparable: `_django_ref/education-website/.github/PULL_REQUEST_TEMPLATE.md`
Owner note: remove this
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: already absent from legacy-site-source.

5. `.github/WORKFLOWS.md`
Status: Likely replacement
Current comparable: `_django_ref/education-website/.github/WORKFLOWS.md`
Owner note: remove this
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: already absent from legacy-site-source.

6. `.github/aw/imports/.gitattributes`
Status: Likely replacement
Current comparable: `_django_ref/education-website/.gitattributes`
Owner note: remove this
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: already absent from legacy-site-source.

7. `.github/aw/imports/github/gh-aw/852cb06ad52958b402ed982b69957ffc57ca0619/.github_workflows_shared_mood.md`
Status: Likely replacement
Current comparable: `_django_ref/education-website/.github/aw/imports/github/gh-aw/852cb06ad52958b402ed982b69957ffc57ca0619/.github_workflows_shared_mood.md`
Owner note: remove this
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: already absent from legacy-site-source.

8. `.github/copilot-instructions.md`
Status: Likely replacement
Current comparable: `_django_ref/education-website/.github/copilot-instructions.md`
Owner note: remove this
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: already absent from legacy-site-source.

9. `.github/copilot-setup-steps.yml`
Status: Likely replacement
Current comparable: `_django_ref/education-website/.github/copilot-setup-steps.yml`
Owner note: remov ethis
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: already absent from legacy-site-source.

10. `.github/workflows/check-migrations.yml`
Status: Likely replacement
Current comparable: `_django_ref/education-website/.github/workflows/check-migrations.yml`
Owner note: remove this
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: already absent from legacy-site-source.

11. `.github/workflows/codeql.yml`
Status: Likely replacement
Current comparable: `_django_ref/education-website/.github/workflows/codeql.yml`
Owner note: remove this
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: already absent from legacy-site-source.

12. `.github/workflows/daily-assign.yml`
Status: Likely replacement
Current comparable: `_django_ref/education-website/.github/workflows/daily-assign.yml`
Owner note: remove this
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: already absent from legacy-site-source.

13. `.github/workflows/delete-unauthorized-issues.yml`
Status: Likely replacement
Current comparable: `_django_ref/education-website/.github/workflows/delete-unauthorized-issues.yml`
Owner note: remove this
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: already absent from legacy-site-source.

14. `.github/workflows/deploy-production.yml`
Status: Likely replacement
Current comparable: `_django_ref/education-website/.github/workflows/deploy-production.yml`
Owner note: remove this
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: already absent from legacy-site-source.

15. `.github/workflows/docker-test.yml`
Status: Likely replacement
Current comparable: `_django_ref/education-website/.github/workflows/docker-test.yml`
Owner note: remove this
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: already absent from legacy-site-source.

16. `.github/workflows/enforce-issue-linked-pr.yml`
Status: Likely replacement
Current comparable: `_django_ref/education-website/.github/workflows/enforce-issue-linked-pr.yml`
Owner note: remove this
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: already absent from legacy-site-source.

17. `.github/workflows/issue-monster.lock.yml`
Status: Likely replacement
Current comparable: `_django_ref/education-website/.github/workflows/issue-monster.lock.yml`
Owner note: remove this
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: already absent from legacy-site-source.

18. `.github/workflows/issue-monster.md`
Status: Likely replacement
Current comparable: `_django_ref/education-website/.github/workflows/issue-monster.md`
Owner note: remove this
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: already absent from legacy-site-source.

19. `.github/workflows/label-issues-by-date.yml`
Status: Likely replacement
Current comparable: `_django_ref/education-website/.github/workflows/label-issues-by-date.yml`
Owner note: remove this
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: already absent from legacy-site-source.

20. `.github/workflows/label-issues.yml`
Status: Likely replacement
Current comparable: `_django_ref/education-website/.github/workflows/label-issues.yml`
Owner note: remove this
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: already absent from legacy-site-source.

21. `.github/workflows/pr-file-count-labeler.yml`
Status: Likely replacement
Current comparable: `_django_ref/education-website/.github/workflows/pr-file-count-labeler.yml`
Owner note: remove this
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: already absent from legacy-site-source.

22. `.github/workflows/pre-commit.yml`
Status: Likely replacement
Current comparable: `_django_ref/education-website/.github/workflows/pre-commit.yml`
Owner note: remove this
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: already absent from legacy-site-source.

23. `.github/workflows/test.yml`
Status: Likely replacement
Current comparable: `_django_ref/education-website/.github/workflows/test.yml`
Owner note: keep this and adjust it to work with the new cloudflare site
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: already absent from legacy-site-source.

24. `.gitignore`
Status: Likely replacement
Current comparable: `.gitignore`
Owner note: keep this combine it
Next step: Done: Combined current ignore rules and protected local env/secrets. Source status: removed from legacy-site-source.

25. `.pre-commit-config.yaml`
Status: Likely replacement
Current comparable: `_django_ref/education-website/.pre-commit-config.yaml`
Owner note: keep this integrate it into the new site so we have a precommit check
Next step: Done: Moved pre-commit config into current project. Source status: removed from legacy-site-source.

26. `.prettierignore`
Status: Likely replacement
Current comparable: `_django_ref/education-website/.prettierignore`
Owner note: keep this
Next step: Done: Moved formatting ignore config into current project. Source status: removed from legacy-site-source.

27. `.vscode/extensions.json`
Status: Likely replacement
Current comparable: `_django_ref/education-website/.vscode/extensions.json`
Owner note: remove this
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: already absent from legacy-site-source.

28. `.vscode/tasks.json`
Status: Likely replacement
Current comparable: `_django_ref/education-website/.vscode/tasks.json`
Owner note: remove this
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: already absent from legacy-site-source.

29. `AGENTS.md`
Status: Likely replacement
Current comparable: `_django_ref/education-website/AGENTS.md`
Owner note: remove this
Next step: Done: Owner decision says remove/delete; removed from legacy source. Source status: already absent from legacy-site-source.

30. `CODE_OF_CONDUCT.md`
Status: Likely replacement
Current comparable: `_django_ref/education-website/CODE_OF_CONDUCT.md`
Owner note: keep it move it to current site
Next step: Done: Moved community policy into current project. Source status: removed from legacy-site-source.

31. `CONTRIBUTING.md`
Status: Likely replacement
Current comparable: `CONTRIBUTING.md`
Owner note: keep and move to current site, update it
Next step: Done: Current project already has/keeps contribution docs. Source status: removed from legacy-site-source.

32. `Dockerfile`
Status: Likely replacement
Current comparable: `_django_ref/education-website/Dockerfile`
Owner note: remove all docker stuff
Next step: Done: Legacy runtime/deployment/reference artifact removed from current migration scope. Source status: already absent from legacy-site-source.

33. `FUNDING.yml`
Status: Likely replacement
Current comparable: `_django_ref/education-website/FUNDING.yml`
Owner note: keep this and move to current site
Next step: Done: Moved funding metadata into current project. Source status: removed from legacy-site-source.

34. `LICENSE`
Status: Likely replacement
Current comparable: `LICENSE`
Owner note: keep and move
Next step: Done: Current project keeps license. Source status: removed from legacy-site-source.

35. `README.md`
Status: Likely replacement
Current comparable: `README.md`
Owner note: keep, move and update
Next step: Done: Current project keeps README; future README improvements belong outside legacy source. Source status: removed from legacy-site-source.

36. `ansible/ansible.cfg`
Status: Likely replacement
Current comparable: `_django_ref/education-website/ansible/ansible.cfg`
Owner note: remove all ansible stuff
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: already absent from legacy-site-source.

37. `ansible/deploy.sh`
Status: Likely replacement
Current comparable: `_django_ref/education-website/ansible/deploy.sh`
Owner note: remove all ansible stuff
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: already absent from legacy-site-source.

38. `ansible/education-website.service.j2`
Status: Likely replacement
Current comparable: `_django_ref/education-website/ansible/education-website.service.j2`
Owner note: remove all ansible stuff
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: already absent from legacy-site-source.

39. `ansible/nginx-http.conf.j2`
Status: Likely replacement
Current comparable: `_django_ref/education-website/ansible/nginx-http.conf.j2`
Owner note: remove all ansible stuff
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: already absent from legacy-site-source.

40. `ansible/playbook.yml`
Status: Likely replacement
Current comparable: `_django_ref/education-website/ansible/playbook.yml`
Owner note: remove all ansible stuff
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: already absent from legacy-site-source.

41. `ansible/ssh.sh`
Status: Likely replacement
Current comparable: `_django_ref/education-website/ansible/ssh.sh`
Owner note: remove all ansible stuff
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: already absent from legacy-site-source.

42. `education-website-447605-36bf00ace565.json`
Status: Needs mapping
Current comparable: -
Owner note: move this into current site and delete from legacy
Next step: Done: Moved into local .secrets and gitignored. Source status: already absent from legacy-site-source.

43. `manage.py`
Status: Platform replaced
Current comparable: `src/worker.py`
Owner note: remove this
Next step: Done: Legacy runtime/deployment/reference artifact removed from current migration scope. Source status: already absent from legacy-site-source.

44. `poetry.lock`
Status: Likely replacement
Current comparable: `_django_ref/education-website/poetry.lock`
Owner note: remove this
Next step: Done: Legacy runtime/deployment/reference artifact removed from current migration scope. Source status: already absent from legacy-site-source.

45. `poetry.toml`
Status: Likely replacement
Current comparable: `_django_ref/education-website/poetry.toml`
Owner note: remove this
Next step: Done: Legacy runtime/deployment/reference artifact removed from current migration scope. Source status: already absent from legacy-site-source.

46. `pyproject.toml`
Status: Likely replacement
Current comparable: `_django_ref/education-website/pyproject.toml`
Owner note: remove this
Next step: Done: Legacy runtime/deployment/reference artifact removed from current migration scope. Source status: already absent from legacy-site-source.

47. `run.sh`
Status: Likely replacement
Current comparable: `_django_ref/education-website/run.sh`
Owner note: move it and adjust to cloudflare worker run locally
Next step: Done: Recreated as current Cloudflare Worker local-dev entrypoint. Source status: removed from legacy-site-source.

48. `scripts/assign.py`
Status: Needs review
Current comparable: `src/worker.py`
Owner note: delete it
Next step: Done: Legacy runtime/deployment/reference artifact removed from current migration scope. Source status: already absent from legacy-site-source.

49. `scripts/dump.sql`
Status: Likely replacement
Current comparable: `_django_ref/education-website/scripts/dump.sql`
Owner note: delete it
Next step: Done: Legacy runtime/deployment/reference artifact removed from current migration scope. Source status: already absent from legacy-site-source.

50. `scripts/inserts_only.sql`
Status: Likely replacement
Current comparable: `_django_ref/education-website/scripts/inserts_only.sql`
Owner note: delete it
Next step: Done: Legacy runtime/deployment/reference artifact removed from current migration scope. Source status: already absent from legacy-site-source.

51. `scripts/label_by_date.py`
Status: Needs review
Current comparable: `src/worker.py`
Owner note: delete it
Next step: Done: Legacy runtime/deployment/reference artifact removed from current migration scope. Source status: already absent from legacy-site-source.

52. `scripts/modified_dump.sql`
Status: Likely replacement
Current comparable: `_django_ref/education-website/scripts/modified_dump.sql`
Owner note: delete it
Next step: Done: Legacy runtime/deployment/reference artifact removed from current migration scope. Source status: already absent from legacy-site-source.

53. `scripts/mysql_dump.sql`
Status: Likely replacement
Current comparable: `_django_ref/education-website/scripts/mysql_dump.sql`
Owner note: delete it
Next step: Done: Legacy runtime/deployment/reference artifact removed from current migration scope. Source status: already absent from legacy-site-source.

54. `scripts/postgresql_dump.sql`
Status: Likely replacement
Current comparable: `_django_ref/education-website/scripts/postgresql_dump.sql`
Owner note: delete it
Next step: Done: Legacy runtime/deployment/reference artifact removed from current migration scope. Source status: already absent from legacy-site-source.

55. `static/header.png`
Status: Needs asset decision
Current comparable: -
Owner note: remove it
Next step: Done: Legacy runtime/deployment/reference artifact removed from current migration scope. Source status: already absent from legacy-site-source.

56. `static/images/blue-dot.png`
Status: Needs asset decision
Current comparable: -
Owner note: remove it
Next step: Done: Legacy runtime/deployment/reference artifact removed from current migration scope. Source status: already absent from legacy-site-source.

57. `static/images/default_teacher.png`
Status: Needs asset decision
Current comparable: -
Owner note: remove it
Next step: Done: Legacy runtime/deployment/reference artifact removed from current migration scope. Source status: already absent from legacy-site-source.

58. `static/images/gsoc-logo.png`
Status: Needs asset decision
Current comparable: -
Owner note: keep it - add a gsoc 2027 link on the homepage small on the bottom to go to gsoc.alphaonelabs.com
Next step: Done: Copied to public/images and linked from homepage GSOC 2027 CTA. Source status: removed from legacy-site-source.

59. `static/images/logo-osl.svg`
Status: Likely replacement
Current comparable: `public/images/logo-osl.svg`
Owner note: keep it and make sure it works on the new site (move it)
Next step: Done: Copied to public/images. Source status: removed from legacy-site-source.

60. `static/images/osl-color-horizontal.png`
Status: Needs asset decision
Current comparable: -
Owner note: keep whichever osl one is current on the site
Next step: Done: Copied to public/images as retained OSL asset. Source status: removed from legacy-site-source.

61. `static/images/placeholder.png`
Status: Needs asset decision
Current comparable: -
Owner note: delete it
Next step: Done: Legacy runtime/deployment/reference artifact removed from current migration scope. Source status: already absent from legacy-site-source.

62. `static/images/quiz-illustration.svg`
Status: Needs asset decision
Current comparable: -
Owner note: dele te it
Next step: Done: Legacy runtime/deployment/reference artifact removed from current migration scope. Source status: already absent from legacy-site-source.

63. `static/images/x-logo.svg`
Status: Needs asset decision
Current comparable: -
Owner note: keep or move
Next step: Done: Copied to public/images as retained social/logo asset. Source status: removed from legacy-site-source.

64. `static/js/virtual_classroom.js`
Status: Needs asset decision
Current comparable: -
Owner note: make sure it works on the new site and delete it
Next step: Done: Legacy runtime/deployment/reference artifact removed from current migration scope. Source status: already absent from legacy-site-source.

65. `tests/test_trackers.py`
Status: Needs decision
Current comparable: -
Owner note: remove it
Next step: Done: Legacy runtime/deployment/reference artifact removed from current migration scope. Source status: already absent from legacy-site-source.

66. `web/__init__.py`
Status: Needs review
Current comparable: `src/worker.py`
Owner note: remove it
Next step: Done: Legacy runtime/deployment/reference artifact removed from current migration scope. Source status: already absent from legacy-site-source.

67. `web/admin.py`
Status: First-class replacement
Current comparable: `public/admin.html`
Owner note: remove it
Next step: Done: Legacy runtime/deployment/reference artifact removed from current migration scope. Source status: already absent from legacy-site-source.

68. `web/apps.py`
Status: Platform replaced
Current comparable: `src/worker.py`
Owner note: remove it
Next step: Done: Legacy runtime/deployment/reference artifact removed from current migration scope. Source status: already absent from legacy-site-source.

69. `web/asgi.py`
Status: Needs review
Current comparable: `src/worker.py`
Owner note: remove it
Next step: Done: Legacy runtime/deployment/reference artifact removed from current migration scope. Source status: already absent from legacy-site-source.

70. `web/context_processors.py`
Status: Partial replacement
Current comparable: `public/partials/navbar.html`
Owner note: remove it
Next step: Done: Legacy runtime/deployment/reference artifact removed from current migration scope. Source status: already absent from legacy-site-source.

71. `web/decorators.py`
Status: Needs review
Current comparable: `src/worker.py`
Owner note: remove it
Next step: Done: Legacy runtime/deployment/reference artifact removed from current migration scope. Source status: already absent from legacy-site-source.

72. `web/email_backend.py`
Status: Needs review
Current comparable: `src/worker.py`
Owner note: remove it
Next step: Done: Legacy runtime/deployment/reference artifact removed from current migration scope. Source status: already absent from legacy-site-source.

73. `web/forms.py`
Status: Partial replacement
Current comparable: `src/worker.py`
Owner note: remove it
Next step: Done: Legacy runtime/deployment/reference artifact removed from current migration scope. Source status: already absent from legacy-site-source.

74. `web/forms_additional.py`
Status: Needs review
Current comparable: `src/worker.py`
Owner note: remove it
Next step: Done: Legacy runtime/deployment/reference artifact removed from current migration scope. Source status: already absent from legacy-site-source.

75. `web/management/__init__.py`
Status: Needs review
Current comparable: `src/worker.py`
Owner note: remove it
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: already absent from legacy-site-source.

76. `web/management/commands/__init__.py`
Status: Reference only
Current comparable: `scripts/`
Owner note: remove it
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: already absent from legacy-site-source.

77. `web/management/commands/cleanup_abandoned_drafts.py`
Status: Reference only
Current comparable: `scripts/`
Owner note: remove it
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: already absent from legacy-site-source.

78. `web/management/commands/create_test_data.py`
Status: Reference only
Current comparable: `scripts/`
Owner note: remove it
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: already absent from legacy-site-source.

79. `web/management/commands/dbdiag.py`
Status: Reference only
Current comparable: `scripts/`
Owner note: remove it
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: already absent from legacy-site-source.

80. `web/management/commands/populate_challenges.py`
Status: Reference only
Current comparable: `scripts/`
Owner note: remove it
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: already absent from legacy-site-source.

81. `web/management/commands/roll_forward_sessions.py`
Status: Reference only
Current comparable: `scripts/`
Owner note: remove it
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: already absent from legacy-site-source.

82. `web/management/commands/run_daily.py`
Status: Reference only
Current comparable: `scripts/`
Owner note: remove it
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: already absent from legacy-site-source.

83. `web/management/commands/send_assignment_reminders.py`
Status: Reference only
Current comparable: `scripts/`
Owner note: setup a cron to send reminders
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: already absent from legacy-site-source.

84. `web/management/commands/send_session_reminders.py`
Status: Reference only
Current comparable: `scripts/`
Owner note: setup a cron to send reminders
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: already absent from legacy-site-source.

85. `web/management/commands/send_verification_reminders.py`
Status: Reference only
Current comparable: `scripts/`
Owner note: setup a cron to send reminders
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: already absent from legacy-site-source.

86. `web/management/commands/send_weekly_updates.py`
Status: Reference only
Current comparable: `scripts/`
Owner note: setup a cron to send reminders
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: already absent from legacy-site-source.

87. `web/master_key.py`
Status: Needs review
Current comparable: `src/worker.py`
Owner note: not srue I think we can delete
Next step: Done: Owner decision says remove/delete; removed from legacy source. Source status: removed from legacy-site-source.

88. `web/middleware.py`
Status: Platform replaced
Current comparable: `src/worker.py`
Owner note: remove
Next step: Done: Legacy runtime/deployment/reference artifact removed from current migration scope. Source status: already absent from legacy-site-source.

89. `web/migrations/0001_initial.py`
Status: Reference only
Current comparable: `src/worker.py`
Owner note: remove
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: already absent from legacy-site-source.

90. `web/migrations/0002_add_unique_email_constraint.py`
Status: Reference only
Current comparable: `src/worker.py`
Owner note: remove
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: already absent from legacy-site-source.

91. `web/migrations/0003_sessionenrollment.py`
Status: Reference only
Current comparable: `src/worker.py`
Owner note: remove
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: already absent from legacy-site-source.

92. `web/migrations/0004_enrollment_payment_intent_id.py`
Status: Reference only
Current comparable: `src/worker.py`
Owner note: remove
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: already absent from legacy-site-source.

93. `web/migrations/0005_alter_course_description_and_more.py`
Status: Reference only
Current comparable: `src/worker.py`
Owner note: remove
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: already absent from legacy-site-source.

94. `web/migrations/0006_alter_course_created_at.py`
Status: Reference only
Current comparable: `src/worker.py`
Owner note: remove
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: already absent from legacy-site-source.

95. `web/migrations/0007_alter_course_image.py`
Status: Reference only
Current comparable: `src/worker.py`
Owner note: remove
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: already absent from legacy-site-source.

96. `web/migrations/0008_profile_avatar.py`
Status: Reference only
Current comparable: `src/worker.py`
Owner note: remove
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: already absent from legacy-site-source.

97. `web/migrations/0009_profile_commission_rate_profile_stripe_account_id_and_more.py`
Status: Reference only
Current comparable: `src/worker.py`
Owner note: remove
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: already absent from legacy-site-source.

98. `web/migrations/0010_course_invite_only.py`
Status: Reference only
Current comparable: `src/worker.py`
Owner note: remove
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: already absent from legacy-site-source.

99. `web/migrations/0011_coursematerial_external_url_and_more.py`
Status: Reference only
Current comparable: `src/worker.py`
Owner note: remove
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: already absent from legacy-site-source.

100. `web/migrations/0012_searchlog.py`
Status: Purposefully reduced
Current comparable: -
Owner note: remove
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: already absent from legacy-site-source.

101. `web/migrations/0013_webrequest.py`
Status: Purposefully omitted
Current comparable: -
Owner note: remove
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: already absent from legacy-site-source.

102. `web/migrations/0014_session_enable_rollover_session_is_rolled_over_and_more.py`
Status: Reference only
Current comparable: `src/worker.py`
Owner note: remove
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: already absent from legacy-site-source.

103. `web/migrations/0015_profile_referral_code_profile_referral_earnings_and_more.py`
Status: Reference only
Current comparable: `src/worker.py`
Owner note: remove
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: already absent from legacy-site-source.

104. `web/migrations/0016_generate_referral_codes.py`
Status: Reference only
Current comparable: `src/worker.py`
Owner note: remove
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: already absent from legacy-site-source.

105. `web/migrations/0017_add_referral_code_unique_constraint.py`
Status: Reference only
Current comparable: `src/worker.py`
Owner note: remove
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: already absent from legacy-site-source.

106. `web/migrations/0018_alter_blogpost_title_charset.py`
Status: Reference only
Current comparable: `src/worker.py`
Owner note: remove
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: already absent from legacy-site-source.

107. `web/migrations/0019_convert_blogpost_content_to_markdownx.py`
Status: Reference only
Current comparable: `src/worker.py`
Owner note: remove
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: already absent from legacy-site-source.

108. `web/migrations/0019_update_charset_to_utf8mb4.py`
Status: Reference only
Current comparable: `src/worker.py`
Owner note: remove
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: already absent from legacy-site-source.

109. `web/migrations/0020_merge_20250210_0424.py`
Status: Reference only
Current comparable: `src/worker.py`
Owner note: remove
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: already absent from legacy-site-source.

110. `web/migrations/0021_challenge_challengesubmission.py`
Status: Reference only
Current comparable: `src/worker.py`
Owner note: remove
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: already absent from legacy-site-source.

111. `web/migrations/0022_goods_alter_cartitem_unique_together_cartitem_goods_and_more.py`
Status: Purposefully omitted
Current comparable: -
Owner note: remove
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: already absent from legacy-site-source.

112. `web/migrations/0023_donation.py`
Status: Reference only
Current comparable: `src/worker.py`
Owner note: remove
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: already absent from legacy-site-source.

113. `web/migrations/0024_create_success_story.py`
Status: Reference only
Current comparable: `src/worker.py`
Owner note: remove
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: already absent from legacy-site-source.

114. `web/migrations/0025_progresstracker.py`
Status: Reference only
Current comparable: `src/worker.py`
Owner note: remove
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: already absent from legacy-site-source.

115. `web/migrations/0026_enhance_meme_model.py`
Status: Reference only
Current comparable: `src/worker.py`
Owner note: remove
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: already absent from legacy-site-source.

116. `web/migrations/0027_educationalvideo.py`
Status: Reference only
Current comparable: `src/worker.py`
Owner note: remove
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: already absent from legacy-site-source.

117. `web/migrations/0028_certificate.py`
Status: Reference only
Current comparable: `src/worker.py`
Owner note: remove
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: already absent from legacy-site-source.

118. `web/migrations/0029_learningstreak.py`
Status: Reference only
Current comparable: `src/worker.py`
Owner note: remove
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: already absent from legacy-site-source.

119. `web/migrations/0030_quiz_quizquestion_quizoption_userquiz.py`
Status: Reference only
Current comparable: `src/worker.py`
Owner note: remove
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: already absent from legacy-site-source.

120. `web/migrations/0031_achievement_badge_icon_and_more.py`
Status: Reference only
Current comparable: `src/worker.py`
Owner note: remove
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: already absent from legacy-site-source.

121. `web/migrations/0032_rename_completion_date_teamgoalmember_completed_at_and_more.py`
Status: Reference only
Current comparable: `src/worker.py`
Owner note: remove
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: already absent from legacy-site-source.

122. `web/migrations/0033_gradeablelink_linkgrade.py`
Status: Reference only
Current comparable: `src/worker.py`
Owner note: remove
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: already absent from legacy-site-source.

123. `web/migrations/0034_profile_is_profile_public.py`
Status: Reference only
Current comparable: `src/worker.py`
Owner note: remove
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: already absent from legacy-site-source.

124. `web/migrations/0035_badge_userbadge.py`
Status: Reference only
Current comparable: `src/worker.py`
Owner note: remove
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: already absent from legacy-site-source.

125. `web/migrations/0036_peerchallenge_peerchallengeinvitation.py`
Status: Reference only
Current comparable: `src/worker.py`
Owner note: remove
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: already absent from legacy-site-source.

126. `web/migrations/0037_profile_how_did_you_hear_about_us.py`
Status: Reference only
Current comparable: `src/worker.py`
Owner note: remove
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: already absent from legacy-site-source.

127. `web/migrations/0038_coursematerial_due_date_and_more.py`
Status: Reference only
Current comparable: `src/worker.py`
Owner note: remove
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: already absent from legacy-site-source.

128. `web/migrations/0039_notehistory.py`
Status: Reference only
Current comparable: `src/worker.py`
Owner note: remove
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: already absent from legacy-site-source.

129. `web/migrations/0040_challengesubmission_points_awarded_and_more.py`
Status: Reference only
Current comparable: `src/worker.py`
Owner note: remove
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: already absent from legacy-site-source.

130. `web/migrations/0041_challenge_challenge_type_alter_challenge_week_number_and_more.py`
Status: Reference only
Current comparable: `src/worker.py`
Owner note: remove
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: already absent from legacy-site-source.

131. `web/migrations/0042_profile_avatar_accessories_and_more.py`
Status: Reference only
Current comparable: `src/worker.py`
Owner note: remove
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: already absent from legacy-site-source.

132. `web/migrations/0043_alter_studygroup_members_studygroupinvite.py`
Status: Reference only
Current comparable: `src/worker.py`
Owner note: remove
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: already absent from legacy-site-source.

133. `web/migrations/0044_waitingroom_fulfilled_course.py`
Status: Reference only
Current comparable: `src/worker.py`
Owner note: remove
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: already absent from legacy-site-source.

134. `web/migrations/0045_add_membership_models.py`
Status: Reference only
Current comparable: `src/worker.py`
Owner note: remove
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: already absent from legacy-site-source.

135. `web/migrations/0046_featurevote.py`
Status: Reference only
Current comparable: `src/worker.py`
Owner note: remove
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: already absent from legacy-site-source.

136. `web/migrations/0047_review_is_featured.py`
Status: Reference only
Current comparable: `src/worker.py`
Owner note: remove
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: already absent from legacy-site-source.

137. `web/migrations/0048_scheduledpost_profile_is_social_media_manager.py`
Status: Reference only
Current comparable: `src/worker.py`
Owner note: remove
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: already absent from legacy-site-source.

138. `web/migrations/0049_session_latitude_session_longitude_and_more.py`
Status: Reference only
Current comparable: `src/worker.py`
Owner note: remove
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: already absent from legacy-site-source.

139. `web/migrations/0050_profile_discord_username_profile_github_username_and_more.py`
Status: Reference only
Current comparable: `src/worker.py`
Owner note: remove
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: already absent from legacy-site-source.

140. `web/migrations/0051_teamgoalmember_completion_image_and_more.py`
Status: Reference only
Current comparable: `src/worker.py`
Owner note: remove
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: already absent from legacy-site-source.

141. `web/migrations/0052_add_meme_slug.py`
Status: Reference only
Current comparable: `src/worker.py`
Owner note: remove
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: already absent from legacy-site-source.

142. `web/migrations/0053_goods_featured.py`
Status: Purposefully omitted
Current comparable: -
Owner note: remove
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: already absent from legacy-site-source.

143. `web/migrations/0054_discount.py`
Status: Reference only
Current comparable: `src/worker.py`
Owner note: remove
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: already absent from legacy-site-source.

144. `web/migrations/0055_peermessage_encrypted_key_peermessage_read_at_and_more.py`
Status: Reference only
Current comparable: `src/worker.py`
Owner note: remove
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: already absent from legacy-site-source.

145. `web/migrations/0056_forumvote.py`
Status: Reference only
Current comparable: `src/worker.py`
Owner note: remove
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: already absent from legacy-site-source.

146. `web/migrations/0057_alter_educationalvideo_uploader.py`
Status: Reference only
Current comparable: `src/worker.py`
Owner note: remove
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: already absent from legacy-site-source.

147. `web/migrations/0058_forumtopic_github_issue_url_and_more.py`
Status: Reference only
Current comparable: `src/worker.py`
Owner note: remove
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: already absent from legacy-site-source.

148. `web/migrations/0059_alter_educationalvideo_description.py`
Status: Reference only
Current comparable: `src/worker.py`
Owner note: remove
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: already absent from legacy-site-source.

149. `web/migrations/0060_question_choice_response_survey_question_survey.py`
Status: Reference only
Current comparable: `src/worker.py`
Owner note: remove
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: already absent from legacy-site-source.

150. `web/migrations/0061_alter_educationalvideo_description_videorequest.py`
Status: Reference only
Current comparable: `src/worker.py`
Owner note: remove
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: already absent from legacy-site-source.

151. `web/migrations/0062_update_waitingroom_for_sessions.py`
Status: Reference only
Current comparable: `src/worker.py`
Owner note: remove
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: already absent from legacy-site-source.

152. `web/migrations/0063_virtualclassroom_virtualclassroomcustomization_and_more.py`
Status: Reference only
Current comparable: `src/worker.py`
Owner note: remove
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: already absent from legacy-site-source.

153. `web/migrations/__init__.py`
Status: Reference only
Current comparable: `src/worker.py`
Owner note: remove
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: already absent from legacy-site-source.

154. `web/models.py`
Status: First-class replacement
Current comparable: `src/worker.py`
Owner note: remove confirm we have it all covered unless we omitted
Next step: Done: Comparable current implementation exists and no unresolved owner note remains. Source status: removed from legacy-site-source.

155. `web/signals.py`
Status: Needs review
Current comparable: `src/worker.py`
Owner note: delete we no longer need it
Next step: Done: Legacy runtime/deployment/reference artifact removed from current migration scope. Source status: already absent from legacy-site-source.

156. `web/static/css/markdown.css`
Status: Needs asset decision
Current comparable: -
Owner note: make sure we have this all setup and working
Next step: Done: Copied to public/css for current markdown rendering needs. Source status: removed from legacy-site-source.

157. `web/static/images/default-course.jpg`
Status: Needs asset decision
Current comparable: -
Owner note: make sure we have this all setup and working
Next step: Done: Copied to public/images for current fallback course imagery. Source status: removed from legacy-site-source.

158. `web/static/images/features/ai_assistant.jpg`
Status: Needs asset decision
Current comparable: -
Owner note: make sure we have this all setup and working
Next step: Done: Copied to public/images/features. Source status: removed from legacy-site-source.

159. `web/static/images/features/grade_feature.jpg`
Status: Needs asset decision
Current comparable: -
Owner note: make sure we have this all setup and working
Next step: Done: Copied to public/images/features. Source status: removed from legacy-site-source.

160. `web/static/images/features/study_groups.jpg`
Status: Needs asset decision
Current comparable: -
Owner note: make sure we have this all setup and working
Next step: Done: Copied to public/images/features. Source status: removed from legacy-site-source.

161. `web/static/images/logo.png`
Status: Likely replacement
Current comparable: `public/images/logo.png`
Owner note: make sure we have this all setup and working
Next step: Done: Current site already uses public/images/logo.png. Source status: removed from legacy-site-source.

162. `web/static/js/password-toggle.js`
Status: Needs asset decision
Current comparable: -
Owner note: make sure wehave a password toggle
Next step: Done: Replaced by global password toggle installed from base.html. Source status: removed from legacy-site-source.

163. `web/storage.py`
Status: Needs review
Current comparable: `src/worker.py`
Owner note: delete
Next step: Done: Legacy runtime/deployment/reference artifact removed from current migration scope. Source status: already absent from legacy-site-source.

164. `web/templates/404.html`
Status: Needs mapping
Current comparable: -
Owner note: make sure we have this all setup and working  with a similar looking page
Next step: Done: Rebuilt as current public/404.html with base.html styling. Source status: removed from legacy-site-source.

165. `web/templates/429.html`
Status: Needs mapping
Current comparable: -
Owner note: make sure we have this all setup and working  with a simlar page
Next step: Done: Rebuilt as current public/429.html with base.html styling. Source status: removed from legacy-site-source.

166. `web/templates/500.html`
Status: Needs mapping
Current comparable: -
Owner note: make sure we have this all setup and working  with a imslar page
Next step: Done: Rebuilt as current public/500.html with base.html styling and Worker non-API 500 handling. Source status: removed from legacy-site-source.

167. `web/templates/about.html`
Status: First-class replacement
Current comparable: `public/about.html`
Owner note: copy this exactly please
Next step: Done: Copied/restored into current public/about.html. Source status: removed from legacy-site-source.

168. `web/templates/account/delete_account.html`
Status: Partial replacement
Current comparable: `public/profile.html`
Owner note: make sure users can delete accounts
Next step: Done: Replaced by profile page account deletion and DELETE /api/profile. Source status: removed from legacy-site-source.

169. `web/templates/account/login.html`
Status: Partial replacement
Current comparable: `public/profile.html`
Owner note: delete
Next step: Done: Owner decision says remove/delete; removed from legacy source. Source status: removed from legacy-site-source.

170. `web/templates/base.html`
Status: Partial replacement
Current comparable: `public/partials/navbar.html`
Owner note: make sure we have this all setup and working
Next step: Done: Replaced by current public/base.html template renderer. Source status: removed from legacy-site-source.

171. `web/templates/captcha/widget.html`
Status: Needs mapping
Current comparable: -
Owner note: delete
Next step: Done: Owner decision says remove/delete; removed from legacy source. Source status: already absent from legacy-site-source.

172. `web/templates/courses/confirm_rolled_sessions.html`
Status: Partial replacement
Current comparable: `public/activity.html`
Owner note: delete
Next step: Done: Owner decision says remove/delete; removed from legacy source. Source status: removed from legacy-site-source.

173. `web/templates/goods/goods_confirm_delete.html`
Status: Purposefully omitted
Current comparable: -
Owner note: delete all goods stuff
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: already absent from legacy-site-source.

174. `web/templates/goods/goods_create.html`
Status: Purposefully omitted
Current comparable: -
Owner note: delete all goods stuff
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: already absent from legacy-site-source.

175. `web/templates/goods/goods_create_success.html`
Status: Purposefully omitted
Current comparable: -
Owner note: delete all goods stuff
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: already absent from legacy-site-source.

176. `web/templates/goods/goods_detail.html`
Status: Purposefully omitted
Current comparable: -
Owner note: delete all goods stuff
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: already absent from legacy-site-source.

177. `web/templates/goods/goods_form.html`
Status: Purposefully omitted
Current comparable: -
Owner note: delete all goods stuff
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: already absent from legacy-site-source.

178. `web/templates/goods/goods_list.html`
Status: Purposefully omitted
Current comparable: -
Owner note: delete all goods stuff
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: already absent from legacy-site-source.

179. `web/templates/goods/goods_listing.html`
Status: Purposefully omitted
Current comparable: -
Owner note: delete all goods stuff
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: already absent from legacy-site-source.

180. `web/templates/goods/goods_update.html`
Status: Purposefully omitted
Current comparable: -
Owner note: delete all goods stuff
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: already absent from legacy-site-source.

181. `web/templates/gsoc_landing_page.html`
Status: Needs mapping
Current comparable: -
Owner note: moved we can remove this
Next step: Done: Moved off-site; homepage now links to gsoc.alphaonelabs.com. Source status: already absent from legacy-site-source.

182. `web/templates/leaderboards/leaderboards.html`
Status: Needs mapping
Current comparable: -
Owner note: remove leaderboards
Next step: Done: Old leaderboards removed; referral leaderboard remains current. Source status: already absent from legacy-site-source.

183. `web/templates/storefront/storefront_create.html`
Status: Purposefully omitted
Current comparable: -
Owner note: remove all storefront stuff
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: already absent from legacy-site-source.

184. `web/templates/storefront/storefront_detail.html`
Status: Purposefully omitted
Current comparable: -
Owner note: remove all storefront stuff
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: already absent from legacy-site-source.

185. `web/templates/storefront/storefront_form.html`
Status: Purposefully omitted
Current comparable: -
Owner note: remove all storefront stuff
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: already absent from legacy-site-source.

186. `web/templates/storefront/storefront_update.html`
Status: Purposefully omitted
Current comparable: -
Owner note: remove all storefront stuff
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: already absent from legacy-site-source.

187. `web/templates/teams/create.html`
Status: Purposefully omitted
Current comparable: -
Owner note: make sure we have this all setup and working
Next step: Done: Purposefully omitted by product decision; removed from legacy source. Source status: removed from legacy-site-source.

188. `web/templates/teams/delete_confirm.html`
Status: Purposefully omitted
Current comparable: -
Owner note: remove all teams stuff
Next step: Done: Purposefully omitted by product decision; removed from legacy source. Source status: already absent from legacy-site-source.

189. `web/templates/teams/detail.html`
Status: Purposefully omitted
Current comparable: -
Owner note: remove all teams stuff
Next step: Done: Purposefully omitted by product decision; removed from legacy source. Source status: already absent from legacy-site-source.

190. `web/templates/teams/list.html`
Status: Purposefully omitted
Current comparable: -
Owner note: remove all teams stuff
Next step: Done: Purposefully omitted by product decision; removed from legacy source. Source status: already absent from legacy-site-source.

191. `web/templates/teams/submit_proof.html`
Status: Purposefully omitted
Current comparable: -
Owner note: remove all teams stuff
Next step: Done: Purposefully omitted by product decision; removed from legacy source. Source status: already absent from legacy-site-source.

192. `web/templates/terms.html`
Status: First-class replacement
Current comparable: `public/terms.html`
Owner note: copy the terms as exact
Next step: Done: Copied/restored into current public/terms.html. Source status: removed from legacy-site-source.

193. `web/templates/videos/list.html`
Status: Needs mapping
Current comparable: -
Owner note: delete videos are now activities
Next step: Done: Videos are now Activity records. Source status: already absent from legacy-site-source.

194. `web/templates/videos/request_list.html`
Status: Needs mapping
Current comparable: -
Owner note: delete videos are now activities
Next step: Done: Video requests are folded into activity/request flows. Source status: already absent from legacy-site-source.

195. `web/templates/videos/submit_request.html`
Status: Needs mapping
Current comparable: -
Owner note: delete videos are now activities
Next step: Done: Video requests are folded into activity/request flows. Source status: already absent from legacy-site-source.

196. `web/templates/videos/upload.html`
Status: Needs mapping
Current comparable: -
Owner note: delete videos are now activities
Next step: Done: Video uploads are folded into activity management decisions. Source status: already absent from legacy-site-source.

197. `web/templates/waiting_rooms.html`
Status: Likely replacement
Current comparable: `public/waiting-rooms.html`
Owner note: all activities can have a waiting room now so this can be managed automatically
Next step: Done: Comparable current implementation exists and no unresolved owner note remains. Source status: removed from legacy-site-source.

198. `web/templates/web/contributor_detail.html`
Status: Needs mapping
Current comparable: -
Owner note: remove the contributor stuff
Next step: Done: Owner decision says remove/delete; removed from legacy source. Source status: removed from legacy-site-source.

199. `web/templates/web/contributors_list.html`
Status: Needs mapping
Current comparable: -
Owner note: remove the contributor stuff
Next step: Done: Owner decision says remove/delete; removed from legacy source. Source status: removed from legacy-site-source.

200. `web/templates/web/peer_challenges/challenge_detail.html`
Status: Needs mapping
Current comparable: -
Owner note: remove peer challenges
Next step: Done: Owner decision says remove/delete; removed from legacy source. Source status: removed from legacy-site-source.

201. `web/templates/web/peer_challenges/invite_participants.html`
Status: Needs mapping
Current comparable: -
Owner note: remove peer challenges
Next step: Done: Owner decision says remove/delete; removed from legacy source. Source status: removed from legacy-site-source.

202. `web/templates/web/peer_challenges/leaderboard.html`
Status: Needs mapping
Current comparable: -
Owner note: remove peer challenges
Next step: Done: Owner decision says remove/delete; removed from legacy source. Source status: removed from legacy-site-source.

203. `web/templates/web/peer_challenges/participant_results.html`
Status: Needs mapping
Current comparable: -
Owner note: remove peer challenges
Next step: Done: Owner decision says remove/delete; removed from legacy source. Source status: removed from legacy-site-source.

204. `web/templates/web/peer_challenges/take_challenge.html`
Status: Needs mapping
Current comparable: -
Owner note: remove peer challenges
Next step: Done: Owner decision says remove/delete; removed from legacy source. Source status: removed from legacy-site-source.

205. `web/templatetags/__init__.py`
Status: Needs review
Current comparable: `src/worker.py`
Owner note: remvoe this
Next step: Done: Legacy runtime/deployment/reference artifact removed from current migration scope. Source status: already absent from legacy-site-source.

206. `web/virtual_lab/__init__.py`
Status: Partial replacement
Current comparable: `public/virtual-classroom.html`
Owner note: virtual labs moved we can link to it check our github
Next step: Done: Old virtual labs moved off-site; current virtual classroom links to GitHub. Source status: removed from legacy-site-source.

207. `web/virtual_lab/apps.py`
Status: Partial replacement
Current comparable: `public/virtual-classroom.html`
Owner note: virtual labs moved we can link to it check our github
Next step: Done: Old virtual labs moved off-site; current virtual classroom links to GitHub. Source status: removed from legacy-site-source.

208. `web/virtual_lab/css/virtual_lab.css`
Status: Partial replacement
Current comparable: `public/virtual-classroom.html`
Owner note: virtual labs moved we can link to it check our github
Next step: Done: Old virtual labs moved off-site; current virtual classroom links to GitHub. Source status: removed from legacy-site-source.

209. `web/virtual_lab/models.py`
Status: Partial replacement
Current comparable: `public/virtual-classroom.html`
Owner note: virtual labs moved we can link to it check our github
Next step: Done: Old virtual labs moved off-site; current virtual classroom links to GitHub. Source status: removed from legacy-site-source.

210. `web/virtual_lab/static/virtual_lab/js/chemistry/ph_indicator.js`
Status: Partial replacement
Current comparable: `public/virtual-classroom.html`
Owner note: virtual labs moved we can link to it check our github
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: removed from legacy-site-source.

211. `web/virtual_lab/static/virtual_lab/js/chemistry/precipitation.js`
Status: Partial replacement
Current comparable: `public/virtual-classroom.html`
Owner note: virtual labs moved we can link to it check our github
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: removed from legacy-site-source.

212. `web/virtual_lab/static/virtual_lab/js/chemistry/reaction_rate.js`
Status: Partial replacement
Current comparable: `public/virtual-classroom.html`
Owner note: virtual labs moved we can link to it check our github
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: removed from legacy-site-source.

213. `web/virtual_lab/static/virtual_lab/js/chemistry/solubility.js`
Status: Partial replacement
Current comparable: `public/virtual-classroom.html`
Owner note: virtual labs moved we can link to it check our github
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: removed from legacy-site-source.

214. `web/virtual_lab/static/virtual_lab/js/chemistry/titration.js`
Status: Partial replacement
Current comparable: `public/virtual-classroom.html`
Owner note: virtual labs moved we can link to it check our github
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: removed from legacy-site-source.

215. `web/virtual_lab/static/virtual_lab/js/code_editor.js`
Status: Partial replacement
Current comparable: `public/virtual-classroom.html`
Owner note: virtual labs moved we can link to it check our github
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: removed from legacy-site-source.

216. `web/virtual_lab/static/virtual_lab/js/common.js`
Status: Partial replacement
Current comparable: `public/virtual-classroom.html`
Owner note: virtual labs moved we can link to it check our github
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: removed from legacy-site-source.

217. `web/virtual_lab/static/virtual_lab/js/physics_electrical_circuit.js`
Status: Partial replacement
Current comparable: `public/virtual-classroom.html`
Owner note: virtual labs moved we can link to it check our github
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: removed from legacy-site-source.

218. `web/virtual_lab/static/virtual_lab/js/physics_inclined.js`
Status: Partial replacement
Current comparable: `public/virtual-classroom.html`
Owner note: virtual labs moved we can link to it check our github
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: removed from legacy-site-source.

219. `web/virtual_lab/static/virtual_lab/js/physics_mass_spring.js`
Status: Partial replacement
Current comparable: `public/virtual-classroom.html`
Owner note: virtual labs moved we can link to it check our github
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: removed from legacy-site-source.

220. `web/virtual_lab/static/virtual_lab/js/physics_pendulum.js`
Status: Partial replacement
Current comparable: `public/virtual-classroom.html`
Owner note: virtual labs moved we can link to it check our github
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: removed from legacy-site-source.

221. `web/virtual_lab/static/virtual_lab/js/physics_projectile.js`
Status: Partial replacement
Current comparable: `public/virtual-classroom.html`
Owner note: virtual labs moved we can link to it check our github
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: removed from legacy-site-source.

222. `web/virtual_lab/templates/virtual_lab/chemistry/index.html`
Status: Partial replacement
Current comparable: `public/virtual-classroom.html`
Owner note: virtual labs moved we can link to it check our github
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: removed from legacy-site-source.

223. `web/virtual_lab/templates/virtual_lab/chemistry/ph_indicator.html`
Status: Partial replacement
Current comparable: `public/virtual-classroom.html`
Owner note: virtual labs moved we can link to it check our github
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: removed from legacy-site-source.

224. `web/virtual_lab/templates/virtual_lab/chemistry/precipitation.html`
Status: Partial replacement
Current comparable: `public/virtual-classroom.html`
Owner note: virtual labs moved we can link to it check our github
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: removed from legacy-site-source.

225. `web/virtual_lab/templates/virtual_lab/chemistry/reaction_rate.html`
Status: Partial replacement
Current comparable: `public/virtual-classroom.html`
Owner note: virtual labs moved we can link to it check our github
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: removed from legacy-site-source.

226. `web/virtual_lab/templates/virtual_lab/chemistry/solubility.html`
Status: Partial replacement
Current comparable: `public/virtual-classroom.html`
Owner note: virtual labs moved we can link to it check our github
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: removed from legacy-site-source.

227. `web/virtual_lab/templates/virtual_lab/chemistry/titration.html`
Status: Partial replacement
Current comparable: `public/virtual-classroom.html`
Owner note: virtual labs moved we can link to it check our github
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: removed from legacy-site-source.

228. `web/virtual_lab/templates/virtual_lab/code_editor/code_editor.html`
Status: Partial replacement
Current comparable: `public/virtual-classroom.html`
Owner note: virtual labs moved we can link to it check our github
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: removed from legacy-site-source.

229. `web/virtual_lab/templates/virtual_lab/home.html`
Status: Partial replacement
Current comparable: `public/virtual-classroom.html`
Owner note: virtual labs moved we can link to it check our github
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: removed from legacy-site-source.

230. `web/virtual_lab/templates/virtual_lab/layout.html`
Status: Partial replacement
Current comparable: `public/virtual-classroom.html`
Owner note: virtual labs moved we can link to it check our github
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: removed from legacy-site-source.

231. `web/virtual_lab/templates/virtual_lab/physics/circuit.html`
Status: Partial replacement
Current comparable: `public/virtual-classroom.html`
Owner note: virtual labs moved we can link to it check our github
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: removed from legacy-site-source.

232. `web/virtual_lab/templates/virtual_lab/physics/inclined.html`
Status: Partial replacement
Current comparable: `public/virtual-classroom.html`
Owner note: virtual labs moved we can link to it check our github
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: removed from legacy-site-source.

233. `web/virtual_lab/templates/virtual_lab/physics/mass_spring.html`
Status: Partial replacement
Current comparable: `public/virtual-classroom.html`
Owner note: virtual labs moved we can link to it check our github
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: removed from legacy-site-source.

234. `web/virtual_lab/templates/virtual_lab/physics/pendulum.html`
Status: Partial replacement
Current comparable: `public/virtual-classroom.html`
Owner note: virtual labs moved we can link to it check our github
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: removed from legacy-site-source.

235. `web/virtual_lab/templates/virtual_lab/physics/projectile.html`
Status: Partial replacement
Current comparable: `public/virtual-classroom.html`
Owner note: virtual labs moved we can link to it check our github
Next step: Done: Legacy path belongs to a removed, platform-replaced, or purposefully omitted area. Source status: removed from legacy-site-source.

236. `web/virtual_lab/tests.py`
Status: Partial replacement
Current comparable: `public/virtual-classroom.html`
Owner note: virtual labs moved we can link to it check our github
Next step: Done: Old virtual labs moved off-site; current virtual classroom links to GitHub. Source status: removed from legacy-site-source.

237. `web/virtual_lab/urls.py`
Status: Partial replacement
Current comparable: `public/virtual-classroom.html`
Owner note: virtual labs moved we can link to it check our github
Next step: Done: Old virtual labs moved off-site; current virtual classroom links to GitHub. Source status: removed from legacy-site-source.

238. `web/virtual_lab/views.py`
Status: Partial replacement
Current comparable: `public/virtual-classroom.html`
Owner note: virtual labs moved we can link to it check our github
Next step: Done: Old virtual labs moved off-site; current virtual classroom links to GitHub. Source status: removed from legacy-site-source.

239. `web/wsgi.py`
Status: Needs review
Current comparable: `src/worker.py`
Owner note: delete this
Next step: Done: Legacy runtime/deployment/reference artifact removed from current migration scope. Source status: already absent from legacy-site-source.
