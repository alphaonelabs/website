# Alpha One Labs Education Platform - Endpoint Analysis
## Executive Summary
Total Endpoints Analyzed: 263
Total Categories: 26

## Categories Overview
- **Admin**: 5 endpoints (Avg Score: 8.0/10)
- **Analytics**: 2 endpoints (Avg Score: 6.0/10)
- **Assessment**: 29 endpoints (Avg Score: 6.0/10)
- **Authentication**: 6 endpoints (Avg Score: 8.7/10)
- **Collaboration**: 10 endpoints (Avg Score: 4.4/10)
- **Communication**: 6 endpoints (Avg Score: 6.8/10)
- **Community**: 31 endpoints (Avg Score: 5.5/10)
- **Content**: 17 endpoints (Avg Score: 4.6/10)
- **Core Pages**: 6 endpoints (Avg Score: 8.8/10)
- **Courses**: 27 endpoints (Avg Score: 7.3/10)
- **Dashboards**: 4 endpoints (Avg Score: 8.5/10)
- **Development**: 2 endpoints (Avg Score: 3.5/10)
- **Discovery**: 3 endpoints (Avg Score: 4.7/10)
- **Feedback**: 9 endpoints (Avg Score: 4.7/10)
- **Gamification**: 4 endpoints (Avg Score: 5.0/10)
- **Infrastructure**: 7 endpoints (Avg Score: 6.9/10)
- **Legacy**: 2 endpoints (Avg Score: 2.0/10)
- **Marketing**: 7 endpoints (Avg Score: 3.7/10)
- **Merchandise**: 15 endpoints (Avg Score: 3.7/10)
- **Payments**: 24 endpoints (Avg Score: 7.1/10)
- **Personalization**: 3 endpoints (Avg Score: 3.3/10)
- **Progress**: 8 endpoints (Avg Score: 7.5/10)
- **Scheduling**: 8 endpoints (Avg Score: 5.5/10)
- **Social**: 4 endpoints (Avg Score: 5.0/10)
- **Tools**: 7 endpoints (Avg Score: 3.9/10)
- **Virtual Classroom**: 17 endpoints (Avg Score: 5.7/10)

---

## Admin

### admin
- **Path**: `admin/`
- **View**: `admin.site.urls`
- **Score**: 10/10 (CRITICAL)
- **Notes**: Critical - Django admin

### admin_dashboard
- **Path**: `admin/dashboard/`
- **View**: `admin_views.admin_dashboard`
- **Score**: 9/10 (CRITICAL)
- **Notes**: Critical - admin dashboard

### system_dashboard
- **Path**: `admin/system/`
- **View**: `admin_views.system_dashboard`
- **Score**: 8/10 (IMPORTANT)
- **Notes**: Important - system dashboard

### system_metrics_api
- **Path**: `admin/system/metrics/`
- **View**: `admin_views.system_metrics_api`
- **Score**: 7/10 (IMPORTANT)
- **Notes**: Important - metrics API

### run_management_command
- **Path**: `admin/system/run/`
- **View**: `admin_views.run_management_command`
- **Score**: 6/10 (USEFUL)
- **Notes**: Useful - run commands

## Analytics

### sales_analytics
- **Path**: `analytics/`
- **View**: `sales_analytics`
- **Score**: 6/10 (USEFUL)
- **Notes**: Useful - sales analytics

### sales_data
- **Path**: `analytics/data/`
- **View**: `sales_data`
- **Score**: 6/10 (USEFUL)
- **Notes**: Useful - analytics data

## Assessment

### take_quiz
- **Path**: `quizzes/<int:quiz_id>/take/`
- **View**: `quiz_views.take_quiz`
- **Score**: 9/10 (CRITICAL)
- **Notes**: Critical - quiz taking

### quiz_list
- **Path**: `quizzes/`
- **View**: `quiz_views.quiz_list`
- **Score**: 8/10 (IMPORTANT)
- **Notes**: Important - quiz listing

### create_quiz
- **Path**: `quizzes/create/`
- **View**: `quiz_views.create_quiz`
- **Score**: 8/10 (IMPORTANT)
- **Notes**: Important - quiz creation

### quiz_detail
- **Path**: `quizzes/<int:quiz_id>/`
- **View**: `quiz_views.quiz_detail`
- **Score**: 8/10 (IMPORTANT)
- **Notes**: Important - quiz detail

### add_question
- **Path**: `quizzes/<int:quiz_id>/add-question/`
- **View**: `quiz_views.add_question`
- **Score**: 8/10 (IMPORTANT)
- **Notes**: Important - question creation

### quiz_results
- **Path**: `quizzes/results/<int:user_quiz_id>/`
- **View**: `quiz_views.quiz_results`
- **Score**: 8/10 (IMPORTANT)
- **Notes**: Important - quiz results

### update_quiz
- **Path**: `quizzes/<int:quiz_id>/update/`
- **View**: `quiz_views.update_quiz`
- **Score**: 7/10 (IMPORTANT)
- **Notes**: Important - quiz editing

### edit_question
- **Path**: `quizzes/questions/<int:question_id>/edit/`
- **View**: `quiz_views.edit_question`
- **Score**: 7/10 (IMPORTANT)
- **Notes**: Important - question editing

### quiz_take_shared
- **Path**: `quizzes/shared/<str:share_code>/`
- **View**: `quiz_views.take_quiz_shared`
- **Score**: 7/10 (IMPORTANT)
- **Notes**: Important - shared quizzes

### grade_short_answer
- **Path**: `quizzes/results/<int:user_quiz_id>/grade/<int:question_id>/`
- **View**: `quiz_views.grade_short_answer`
- **Score**: 7/10 (IMPORTANT)
- **Notes**: Important - manual grading

### delete_quiz
- **Path**: `quizzes/<int:quiz_id>/delete/`
- **View**: `quiz_views.delete_quiz`
- **Score**: 6/10 (USEFUL)
- **Notes**: Useful - quiz deletion

### delete_question
- **Path**: `quizzes/questions/<int:question_id>/delete/`
- **View**: `quiz_views.delete_question`
- **Score**: 6/10 (USEFUL)
- **Notes**: Useful - question deletion

### quiz_analytics
- **Path**: `quizzes/<int:quiz_id>/analytics/`
- **View**: `quiz_views.quiz_analytics`
- **Score**: 6/10 (USEFUL)
- **Notes**: Useful - quiz analytics

### gradeable_link_list
- **Path**: `grade-links/`
- **View**: `GradeableLinkListView.as_view()`
- **Score**: 6/10 (USEFUL)
- **Notes**: Useful - link grading list

### gradeable_link_create
- **Path**: `grade-links/submit/`
- **View**: `GradeableLinkCreateView.as_view()`
- **Score**: 6/10 (USEFUL)
- **Notes**: Useful - submit link

### gradeable_link_detail
- **Path**: `grade-links/<int:pk>/`
- **View**: `GradeableLinkDetailView.as_view()`
- **Score**: 6/10 (USEFUL)
- **Notes**: Useful - link detail

### grade_link
- **Path**: `grade-links/<int:pk>/grade/`
- **View**: `grade_link`
- **Score**: 6/10 (USEFUL)
- **Notes**: Useful - grade link

### challenge_list
- **Path**: `peer-challenges/`
- **View**: `peer_challenge_views.challenge_list`
- **Score**: 5/10 (USEFUL)
- **Notes**: Useful - challenge listing

### create_challenge
- **Path**: `peer-challenges/create/`
- **View**: `peer_challenge_views.create_challenge`
- **Score**: 5/10 (USEFUL)
- **Notes**: Useful - challenge creation

### peer_challenge_detail
- **Path**: `peer-challenges/<int:challenge_id>/`
- **View**: `peer_challenge_views.peer_challenge_detail`
- **Score**: 5/10 (USEFUL)
- **Notes**: Useful - challenge detail

### take_challenge
- **Path**: `peer-challenges/invitation/<int:invitation_id>/take/`
- **View**: `peer_challenge_views.take_challenge`
- **Score**: 5/10 (USEFUL)
- **Notes**: Useful - take challenge

### complete_challenge
- **Path**: `peer-challenges/complete/<int:user_quiz_id>/`
- **View**: `peer_challenge_views.complete_challenge`
- **Score**: 5/10 (USEFUL)
- **Notes**: Useful - complete challenge

### challenge_detail
- **Path**: `challenges/<int:challenge_id>/`
- **View**: `views.challenge_detail`
- **Score**: 5/10 (USEFUL)
- **Notes**: Useful - challenge detail

### challenge_submit
- **Path**: `challenges/<int:challenge_id>/submit/`
- **View**: `views.challenge_submit`
- **Score**: 5/10 (USEFUL)
- **Notes**: Useful - challenge submit

### accept_invitation
- **Path**: `peer-challenges/invitation/<int:invitation_id>/accept/`
- **View**: `peer_challenge_views.accept_invitation`
- **Score**: 4/10 (OPTIONAL)
- **Notes**: Optional - challenge accept

### decline_invitation
- **Path**: `peer-challenges/invitation/<int:invitation_id>/decline/`
- **View**: `peer_challenge_views.decline_invitation`
- **Score**: 4/10 (OPTIONAL)
- **Notes**: Optional - challenge decline

### challenge_leaderboard
- **Path**: `peer-challenges/<int:challenge_id>/leaderboard/`
- **View**: `peer_challenge_views.leaderboard`
- **Score**: 4/10 (OPTIONAL)
- **Notes**: Optional - leaderboard

### submit_to_leaderboard
- **Path**: `peer-challenges/submit-to-leaderboard/<int:user_quiz_id>/`
- **View**: `peer_challenge_views.submit_to_leaderboard`
- **Score**: 4/10 (OPTIONAL)
- **Notes**: Optional - leaderboard submit

### current_weekly_challenge
- **Path**: `current-weekly-challenge/`
- **View**: `views.current_weekly_challenge`
- **Score**: 4/10 (OPTIONAL)
- **Notes**: Optional - weekly challenge

## Authentication

### account_signup
- **Path**: `accounts/signup/`
- **View**: `views.signup_view`
- **Score**: 10/10 (CRITICAL)
- **Notes**: Critical - user registration

### accounts
- **Path**: `accounts/`
- **View**: `allauth.urls`
- **Score**: 10/10 (CRITICAL)
- **Notes**: Critical - login/logout/auth

### profile
- **Path**: `profile/`
- **View**: `views.profile`
- **Score**: 9/10 (CRITICAL)
- **Notes**: Critical - user profile management

### accounts_profile
- **Path**: `accounts/profile/`
- **View**: `views.profile`
- **Score**: 9/10 (CRITICAL)
- **Notes**: Critical - user profile

### delete_account
- **Path**: `accounts/delete/`
- **View**: `views.delete_account`
- **Score**: 7/10 (IMPORTANT)
- **Notes**: Important - account deletion

### notification_preferences
- **Path**: `account/notification-preferences/`
- **View**: `notification_preferences`
- **Score**: 7/10 (IMPORTANT)
- **Notes**: Important - notifications

## Collaboration

### team_goals
- **Path**: `teams/`
- **View**: `views.team_goals`
- **Score**: 5/10 (USEFUL)
- **Notes**: Useful - team goals list

### create_team_goal
- **Path**: `teams/create/`
- **View**: `views.create_team_goal`
- **Score**: 5/10 (USEFUL)
- **Notes**: Useful - create team goal

### team_goal_detail
- **Path**: `teams/<int:goal_id>/`
- **View**: `views.team_goal_detail`
- **Score**: 5/10 (USEFUL)
- **Notes**: Useful - goal detail

### mark_team_contribution
- **Path**: `teams/<int:goal_id>/mark-contribution/`
- **View**: `views.mark_team_contribution`
- **Score**: 5/10 (USEFUL)
- **Notes**: Useful - mark contribution

### accept_team_invite
- **Path**: `teams/invite/<int:invite_id>/accept/`
- **View**: `views.accept_team_invite`
- **Score**: 4/10 (OPTIONAL)
- **Notes**: Optional - accept invite

### decline_team_invite
- **Path**: `teams/invite/<int:invite_id>/decline/`
- **View**: `views.decline_team_invite`
- **Score**: 4/10 (OPTIONAL)
- **Notes**: Optional - decline invite

### delete_team_goal
- **Path**: `teams/<int:goal_id>/delete/`
- **View**: `views.delete_team_goal`
- **Score**: 4/10 (OPTIONAL)
- **Notes**: Optional - delete goal

### remove_team_member
- **Path**: `teams/<int:goal_id>/remove-member/<int:member_id>/`
- **View**: `views.remove_team_member`
- **Score**: 4/10 (OPTIONAL)
- **Notes**: Optional - remove member

### edit_team_goal
- **Path**: `teams/<int:goal_id>/edit/`
- **View**: `views.edit_team_goal`
- **Score**: 4/10 (OPTIONAL)
- **Notes**: Optional - edit goal

### submit_team_proof
- **Path**: `teams/<int:team_goal_id>/submit_proof/`
- **View**: `views.submit_team_proof`
- **Score**: 4/10 (OPTIONAL)
- **Notes**: Optional - submit proof

## Communication

### messaging_dashboard
- **Path**: `messaging/dashboard/`
- **View**: `messaging_dashboard`
- **Score**: 8/10 (IMPORTANT)
- **Notes**: Important - messaging hub

### compose_message
- **Path**: `messaging/compose/`
- **View**: `compose_message`
- **Score**: 8/10 (IMPORTANT)
- **Notes**: Important - message composition

### inbox
- **Path**: `secure/inbox/`
- **View**: `inbox`
- **Score**: 8/10 (IMPORTANT)
- **Notes**: Important - message inbox

### send_encrypted_message
- **Path**: `secure/send/`
- **View**: `send_encrypted_message`
- **Score**: 7/10 (IMPORTANT)
- **Notes**: Important - secure messaging

### download_message
- **Path**: `secure/download/<int:message_id>/`
- **View**: `download_message`
- **Score**: 6/10 (USEFUL)
- **Notes**: Useful - message download

### toggle_star_message
- **Path**: `secure/toggle_star/<int:message_id>/`
- **View**: `toggle_star_message`
- **Score**: 4/10 (OPTIONAL)
- **Notes**: Optional - star messages

## Community

### forum_categories
- **Path**: `forum/`
- **View**: `views.forum_categories`
- **Score**: 7/10 (IMPORTANT)
- **Notes**: Important - forum home

### forum_category
- **Path**: `forum/category/<slug:slug>/`
- **View**: `views.forum_category`
- **Score**: 7/10 (IMPORTANT)
- **Notes**: Important - forum category

### create_topic
- **Path**: `forum/category/<slug:category_slug>/create/`
- **View**: `views.create_topic`
- **Score**: 7/10 (IMPORTANT)
- **Notes**: Important - topic creation

### forum_topic
- **Path**: `forum/<slug:category_slug>/<int:topic_id>/`
- **View**: `views.forum_topic`
- **Score**: 7/10 (IMPORTANT)
- **Notes**: Important - topic view

### create_forum_category
- **Path**: `forum/category/create/`
- **View**: `views.create_forum_category`
- **Score**: 6/10 (USEFUL)
- **Notes**: Useful - forum management

### edit_topic
- **Path**: `forum/topic/<int:topic_id>/edit/`
- **View**: `views.edit_topic`
- **Score**: 6/10 (USEFUL)
- **Notes**: Useful - topic editing

### edit_reply
- **Path**: `forum/reply/<int:reply_id>/edit/`
- **View**: `views.edit_reply`
- **Score**: 6/10 (USEFUL)
- **Notes**: Useful - reply editing

### my_forum_topics
- **Path**: `forum/my-topics/`
- **View**: `views.my_forum_topics`
- **Score**: 6/10 (USEFUL)
- **Notes**: Useful - user topics

### my_forum_replies
- **Path**: `forum/my-replies/`
- **View**: `views.my_forum_replies`
- **Score**: 6/10 (USEFUL)
- **Notes**: Useful - user replies

### peer_connections
- **Path**: `peers/`
- **View**: `views.peer_connections`
- **Score**: 6/10 (USEFUL)
- **Notes**: Useful - peer networking

### send_connection_request
- **Path**: `peers/connect/<int:user_id>/`
- **View**: `views.send_connection_request`
- **Score**: 6/10 (USEFUL)
- **Notes**: Useful - connection requests

### handle_connection_request
- **Path**: `peers/handle/<int:connection_id>/<str:action>/`
- **View**: `views.handle_connection_request`
- **Score**: 6/10 (USEFUL)
- **Notes**: Useful - connection management

### peer_messages
- **Path**: `peers/messages/<int:user_id>/`
- **View**: `views.peer_messages`
- **Score**: 6/10 (USEFUL)
- **Notes**: Useful - peer messaging

### study_groups
- **Path**: `courses/<int:course_id>/groups/`
- **View**: `views.study_groups`
- **Score**: 6/10 (USEFUL)
- **Notes**: Useful - study groups

### study_group_detail
- **Path**: `groups/<int:group_id>/`
- **View**: `views.study_group_detail`
- **Score**: 6/10 (USEFUL)
- **Notes**: Useful - group detail

### all_study_groups
- **Path**: `study-groups/`
- **View**: `views.all_study_groups`
- **Score**: 6/10 (USEFUL)
- **Notes**: Useful - all groups

### create_study_group
- **Path**: `groups/create/`
- **View**: `views.create_study_group`
- **Score**: 6/10 (USEFUL)
- **Notes**: Useful - group creation

### topic_vote
- **Path**: `forum/topic/<int:pk>/vote/`
- **View**: `views.topic_vote`
- **Score**: 5/10 (USEFUL)
- **Notes**: Useful - voting feature

### reply_vote
- **Path**: `forum/reply/<int:pk>/vote/`
- **View**: `views.reply_vote`
- **Score**: 5/10 (USEFUL)
- **Notes**: Useful - voting feature

### invite_to_study_group
- **Path**: `groups/<int:group_id>/invite/`
- **View**: `views.invite_to_study_group`
- **Score**: 5/10 (USEFUL)
- **Notes**: Useful - group invites

### user_invitations
- **Path**: `invitations/`
- **View**: `views.user_invitations`
- **Score**: 5/10 (USEFUL)
- **Notes**: Useful - invitation management

### respond_to_invitation
- **Path**: `invitations/<uuid:invite_id>/respond/`
- **View**: `views.respond_to_invitation`
- **Score**: 5/10 (USEFUL)
- **Notes**: Useful - invitation response

### waiting_room_list
- **Path**: `waiting-rooms/`
- **View**: `views.waiting_room_list`
- **Score**: 5/10 (USEFUL)
- **Notes**: Useful - waiting rooms list

### waiting_room_detail
- **Path**: `waiting-rooms/<int:waiting_room_id>/`
- **View**: `views.waiting_room_detail`
- **Score**: 5/10 (USEFUL)
- **Notes**: Useful - waiting room detail

### join_waiting_room
- **Path**: `waiting-rooms/<int:waiting_room_id>/join/`
- **View**: `views.join_waiting_room`
- **Score**: 5/10 (USEFUL)
- **Notes**: Useful - join waiting room

### create_course_from_waiting_room
- **Path**: `waiting-rooms/<int:waiting_room_id>/create-course/`
- **View**: `views.create_course_from_waiting_room`
- **Score**: 5/10 (USEFUL)
- **Notes**: Useful - course from waiting room

### leave_waiting_room
- **Path**: `waiting-rooms/<int:waiting_room_id>/leave/`
- **View**: `views.leave_waiting_room`
- **Score**: 4/10 (OPTIONAL)
- **Notes**: Optional - leave waiting room

### delete_waiting_room
- **Path**: `waiting-rooms/<int:waiting_room_id>/delete/`
- **View**: `views.delete_waiting_room`
- **Score**: 4/10 (OPTIONAL)
- **Notes**: Optional - delete waiting room

### join_session_waiting_room
- **Path**: `courses/<slug:course_slug>/session-waiting-room/join/`
- **View**: `views.join_session_waiting_room`
- **Score**: 4/10 (OPTIONAL)
- **Notes**: Optional - session waiting

### sync_github_milestones
- **Path**: `forum/sync-milestones/`
- **View**: `views.sync_github_milestones`
- **Score**: 3/10 (OPTIONAL)
- **Notes**: Optional - GitHub integration

### leave_session_waiting_room
- **Path**: `courses/<slug:course_slug>/session-waiting-room/leave/`
- **View**: `views.leave_session_waiting_room`
- **Score**: 3/10 (OPTIONAL)
- **Notes**: Optional - session waiting

## Content

### blog_list
- **Path**: `blog/`
- **View**: `views.blog_list`
- **Score**: 7/10 (IMPORTANT)
- **Notes**: Important - blog listing

### blog_detail
- **Path**: `blog/<slug:slug>/`
- **View**: `views.blog_detail`
- **Score**: 7/10 (IMPORTANT)
- **Notes**: Important - blog post

### create_blog_post
- **Path**: `blog/create/`
- **View**: `views.create_blog_post`
- **Score**: 6/10 (USEFUL)
- **Notes**: Useful - blog creation

### success_story_list
- **Path**: `success-stories/`
- **View**: `views.success_story_list`
- **Score**: 6/10 (USEFUL)
- **Notes**: Useful - success stories

### success_story_detail
- **Path**: `success-stories/<slug:slug>/`
- **View**: `views.success_story_detail`
- **Score**: 6/10 (USEFUL)
- **Notes**: Useful - story detail

### educational_videos_list
- **Path**: `videos/`
- **View**: `views.educational_videos_list`
- **Score**: 6/10 (USEFUL)
- **Notes**: Useful - video list

### blog_tag
- **Path**: `blog/tag/<str:tag>/`
- **View**: `views.blog_tag`
- **Score**: 5/10 (USEFUL)
- **Notes**: Useful - blog tags

### create_success_story
- **Path**: `success-stories/create/`
- **View**: `views.create_success_story`
- **Score**: 5/10 (USEFUL)
- **Notes**: Useful - create story

### upload_educational_video
- **Path**: `videos/upload/`
- **View**: `views.upload_educational_video`
- **Score**: 5/10 (USEFUL)
- **Notes**: Useful - video upload

### edit_success_story
- **Path**: `success-stories/<slug:slug>/edit/`
- **View**: `views.edit_success_story`
- **Score**: 4/10 (OPTIONAL)
- **Notes**: Optional - edit story

### delete_success_story
- **Path**: `success-stories/<slug:slug>/delete/`
- **View**: `views.delete_success_story`
- **Score**: 4/10 (OPTIONAL)
- **Notes**: Optional - delete story

### video_request_list
- **Path**: `videos/requests/`
- **View**: `views.video_request_list`
- **Score**: 4/10 (OPTIONAL)
- **Notes**: Optional - video requests

### submit_video_request
- **Path**: `videos/requests/submit/`
- **View**: `views.submit_video_request`
- **Score**: 4/10 (OPTIONAL)
- **Notes**: Optional - submit request

### fetch_video_title
- **Path**: `fetch-video-title/`
- **View**: `views.fetch_video_title`
- **Score**: 3/10 (OPTIONAL)
- **Notes**: Optional - video metadata

### meme_list
- **Path**: `memes/`
- **View**: `views.meme_list`
- **Score**: 3/10 (OPTIONAL)
- **Notes**: Optional - meme list

### add_meme
- **Path**: `memes/add/`
- **View**: `views.add_meme`
- **Score**: 2/10 (OPTIONAL)
- **Notes**: Optional - add meme

### meme_detail
- **Path**: `memes/<slug:slug>/`
- **View**: `views.meme_detail`
- **Score**: 2/10 (OPTIONAL)
- **Notes**: Optional - meme detail

## Core Pages

### index
- **Path**: ``
- **View**: `views.index`
- **Score**: 10/10 (CRITICAL)
- **Notes**: Critical - homepage

### learn
- **Path**: `learn/`
- **View**: `views.learn`
- **Score**: 10/10 (CRITICAL)
- **Notes**: Critical - main student entry point

### teach
- **Path**: `teach/`
- **View**: `views.teach`
- **Score**: 10/10 (CRITICAL)
- **Notes**: Critical - main teacher entry point

### about
- **Path**: `about/`
- **View**: `views.about`
- **Score**: 8/10 (IMPORTANT)
- **Notes**: Important - site information

### terms
- **Path**: `terms/`
- **View**: `views.terms`
- **Score**: 8/10 (IMPORTANT)
- **Notes**: Important - legal

### feedback
- **Path**: `feedback/`
- **View**: `views.feedback`
- **Score**: 7/10 (IMPORTANT)
- **Notes**: Important - user feedback

## Courses

### create_course
- **Path**: `courses/create/`
- **View**: `views.create_course`
- **Score**: 10/10 (CRITICAL)
- **Notes**: Critical - course creation

### course_detail
- **Path**: `courses/<slug:slug>/`
- **View**: `views.course_detail`
- **Score**: 10/10 (CRITICAL)
- **Notes**: Critical - course detail view

### enroll_course
- **Path**: `courses/<slug:course_slug>/enroll/`
- **View**: `views.enroll_course`
- **Score**: 10/10 (CRITICAL)
- **Notes**: Critical - course enrollment

### course_search
- **Path**: `courses/search/`
- **View**: `views.course_search`
- **Score**: 9/10 (CRITICAL)
- **Notes**: Critical - course discovery

### update_course
- **Path**: `courses/<slug:slug>/edit/`
- **View**: `views.update_course`
- **Score**: 9/10 (CRITICAL)
- **Notes**: Critical - course management

### add_session
- **Path**: `courses/<slug:slug>/add-session/`
- **View**: `views.add_session`
- **Score**: 9/10 (CRITICAL)
- **Notes**: Critical - session creation

### delete_course
- **Path**: `courses/<slug:slug>/delete/`
- **View**: `views.delete_course`
- **Score**: 8/10 (IMPORTANT)
- **Notes**: Important - course deletion

### toggle_course_status
- **Path**: `courses/<slug:slug>/toggle-status/`
- **View**: `views.toggle_course_status`
- **Score**: 8/10 (IMPORTANT)
- **Notes**: Important - course status

### edit_session
- **Path**: `sessions/<int:session_id>/edit/`
- **View**: `views.edit_session`
- **Score**: 8/10 (IMPORTANT)
- **Notes**: Important - session editing

### session_detail
- **Path**: `sessions/<int:session_id>/`
- **View**: `views.session_detail`
- **Score**: 8/10 (IMPORTANT)
- **Notes**: Important - session detail

### message_students
- **Path**: `courses/<slug:slug>/message-students/`
- **View**: `views.message_enrolled_students`
- **Score**: 8/10 (IMPORTANT)
- **Notes**: Important - student communication

### upload_material
- **Path**: `courses/<slug:slug>/materials/upload/`
- **View**: `views.upload_material`
- **Score**: 8/10 (IMPORTANT)
- **Notes**: Important - course materials

### download_material
- **Path**: `courses/<slug:slug>/materials/<int:material_id>/download/`
- **View**: `views.download_material`
- **Score**: 8/10 (IMPORTANT)
- **Notes**: Important - material access

### add_student_to_course
- **Path**: `courses/<slug:slug>/add-student/`
- **View**: `views.add_student_to_course`
- **Score**: 7/10 (IMPORTANT)
- **Notes**: Important - manual enrollment

### student_management
- **Path**: `courses/<slug:course_slug>/manage-student/<int:student_id>/`
- **View**: `views.student_management`
- **Score**: 7/10 (IMPORTANT)
- **Notes**: Important - student management

### message_teacher
- **Path**: `teachers/<int:teacher_id>/message/`
- **View**: `views.message_teacher`
- **Score**: 7/10 (IMPORTANT)
- **Notes**: Important - teacher communication

### course_analytics
- **Path**: `courses/<slug:slug>/analytics/`
- **View**: `views.course_analytics`
- **Score**: 7/10 (IMPORTANT)
- **Notes**: Useful - course insights

### delete_material
- **Path**: `courses/<slug:slug>/materials/<int:material_id>/delete/`
- **View**: `views.delete_material`
- **Score**: 7/10 (IMPORTANT)
- **Notes**: Important - material management

### add_review
- **Path**: `courses/<slug:slug>/reviews/add/`
- **View**: `views.add_review`
- **Score**: 7/10 (IMPORTANT)
- **Notes**: Important - reviews

### duplicate_session
- **Path**: `sessions/<int:session_id>/duplicate/`
- **View**: `views.duplicate_session`
- **Score**: 6/10 (USEFUL)
- **Notes**: Useful - session duplication

### edit_review
- **Path**: `courses/<slug:slug>/reviews/<int:review_id>/edit/`
- **View**: `views.edit_review`
- **Score**: 6/10 (USEFUL)
- **Notes**: Useful - review editing

### delete_review
- **Path**: `courses/<slug:slug>/reviews/<int:review_id>/delete/`
- **View**: `views.delete_review`
- **Score**: 6/10 (USEFUL)
- **Notes**: Useful - review deletion

### invite_student
- **Path**: `courses/<int:course_id>/invite/`
- **View**: `views.invite_student`
- **Score**: 6/10 (USEFUL)
- **Notes**: Useful - student invitation

### confirm_rolled_sessions
- **Path**: `courses/<slug:slug>/confirm-rolled-sessions/`
- **View**: `views.confirm_rolled_sessions`
- **Score**: 5/10 (USEFUL)
- **Notes**: Useful - session management

### course_marketing
- **Path**: `courses/<slug:slug>/marketing/`
- **View**: `views.course_marketing`
- **Score**: 5/10 (USEFUL)
- **Notes**: Useful - marketing tools

### add_featured_review
- **Path**: `courses/<slug:slug>/reviews/<int:review_id>/add-featured-review/`
- **View**: `views.add_featured_review`
- **Score**: 4/10 (OPTIONAL)
- **Notes**: Optional - featured reviews

### remove_featured_review
- **Path**: `courses/<slug:slug>/reviews/<int:review_id>/remove-featured-review/`
- **View**: `views.remove_featured_review`
- **Score**: 4/10 (OPTIONAL)
- **Notes**: Optional - featured reviews

## Dashboards

### student_dashboard
- **Path**: `dashboard/student/`
- **View**: `views.student_dashboard`
- **Score**: 10/10 (CRITICAL)
- **Notes**: Critical - main student dashboard

### teacher_dashboard
- **Path**: `dashboard/teacher/`
- **View**: `views.teacher_dashboard`
- **Score**: 10/10 (CRITICAL)
- **Notes**: Critical - main teacher dashboard

### content_dashboard
- **Path**: `dashboard/content/`
- **View**: `views.content_dashboard`
- **Score**: 7/10 (IMPORTANT)
- **Notes**: Useful - content creator dashboard

### progress_visualization
- **Path**: `dashboard/progress/`
- **View**: `views.progress_visualization`
- **Score**: 7/10 (IMPORTANT)
- **Notes**: Useful - progress tracking

## Development

### create_test_data
- **Path**: `create-test-data/`
- **View**: `views.run_create_test_data`
- **Score**: 5/10 (USEFUL)
- **Notes**: Useful - test data

### test_sentry
- **Path**: `test-sentry-error/`
- **View**: `lambda`
- **Score**: 2/10 (OPTIONAL)
- **Notes**: Optional - sentry testing

## Discovery

### subjects
- **Path**: `subjects/`
- **View**: `views.subjects`
- **Score**: 6/10 (USEFUL)
- **Notes**: Useful - subjects list

### classes_map
- **Path**: `classes-map/`
- **View**: `views.classes_map`
- **Score**: 4/10 (OPTIONAL)
- **Notes**: Optional - classes map

### map_data_api
- **Path**: `api/map-data/`
- **View**: `views.map_data_api`
- **Score**: 4/10 (OPTIONAL)
- **Notes**: Optional - map data API

## Feedback

### surveys
- **Path**: `surveys/`
- **View**: `SurveyListView.as_view()`
- **Score**: 5/10 (USEFUL)
- **Notes**: Useful - survey list

### survey-create
- **Path**: `surveys/create/`
- **View**: `SurveyCreateView.as_view()`
- **Score**: 5/10 (USEFUL)
- **Notes**: Useful - survey creation

### survey-detail
- **Path**: `surveys/<int:pk>/`
- **View**: `SurveyDetailView.as_view()`
- **Score**: 5/10 (USEFUL)
- **Notes**: Useful - survey detail

### submit-survey
- **Path**: `surveys/<int:pk>/submit/`
- **View**: `submit_survey`
- **Score**: 5/10 (USEFUL)
- **Notes**: Useful - survey submit

### survey-results
- **Path**: `surveys/<int:pk>/results/`
- **View**: `SurveyResultsView.as_view()`
- **Score**: 5/10 (USEFUL)
- **Notes**: Useful - survey results

### features
- **Path**: `features/`
- **View**: `features_page`
- **Score**: 5/10 (USEFUL)
- **Notes**: Useful - features page

### survey-delete
- **Path**: `surveys/<int:pk>/delete/`
- **View**: `SurveyDeleteView.as_view()`
- **Score**: 4/10 (OPTIONAL)
- **Notes**: Optional - survey deletion

### feature_vote
- **Path**: `features/vote/`
- **View**: `feature_vote`
- **Score**: 4/10 (OPTIONAL)
- **Notes**: Optional - vote feature

### feature_vote_count
- **Path**: `features/vote-count/`
- **View**: `feature_vote_count`
- **Score**: 4/10 (OPTIONAL)
- **Notes**: Optional - vote count

## Gamification

### streak_detail
- **Path**: `streak/`
- **View**: `streak_detail`
- **Score**: 5/10 (USEFUL)
- **Notes**: Useful - engagement feature

### leaderboards
- **Path**: `leaderboards/`
- **View**: `views.all_leaderboards`
- **Score**: 5/10 (USEFUL)
- **Notes**: Useful - leaderboards

### award_achievement
- **Path**: `award-achievement/`
- **View**: `views.award_achievement`
- **Score**: 5/10 (USEFUL)
- **Notes**: Useful - award achievement

### award_badge
- **Path**: `award-badge/`
- **View**: `views.award_badge`
- **Score**: 5/10 (USEFUL)
- **Notes**: Useful - award badge

## Infrastructure

### i18n
- **Path**: `i18n/`
- **View**: `django.conf.urls.i18n`
- **Score**: 10/10 (CRITICAL)
- **Notes**: Critical - language selection

### captcha
- **Path**: `captcha/`
- **View**: `captcha.urls`
- **Score**: 9/10 (CRITICAL)
- **Notes**: Critical - security/anti-spam

### markdownx
- **Path**: `markdownx/`
- **View**: `markdownx.urls`
- **Score**: 7/10 (IMPORTANT)
- **Notes**: Important - content editing

### system_status
- **Path**: `status/`
- **View**: `views.system_status`
- **Score**: 7/10 (IMPORTANT)
- **Notes**: Important - system status

### github_update
- **Path**: `github_update/`
- **View**: `views.github_update`
- **Score**: 6/10 (USEFUL)
- **Notes**: Webhook - CI/CD integration

### sitemap
- **Path**: `sitemap/`
- **View**: `views.sitemap`
- **Score**: 6/10 (USEFUL)
- **Notes**: Useful - sitemap

### sync_github_milestones
- **Path**: `sync_github_milestones/`
- **View**: `views.sync_github_milestones`
- **Score**: 3/10 (OPTIONAL)
- **Notes**: Optional - GitHub sync

## Legacy

### classroom_whiteboard_legacy
- **Path**: `whiteboard/<int:classroom_id>/`
- **View**: `RedirectView`
- **Score**: 2/10 (OPTIONAL)
- **Notes**: Deprecated - legacy redirect

### update_student_attendance_legacy
- **Path**: `update_student_attendance/<int:classroom_id>/`
- **View**: `RedirectView`
- **Score**: 2/10 (OPTIONAL)
- **Notes**: Deprecated - legacy redirect

## Marketing

### handle_referral
- **Path**: `ref/<str:code>/`
- **View**: `views.handle_referral`
- **Score**: 6/10 (USEFUL)
- **Notes**: Useful - referral tracking

### apply_discount_via_referrer
- **Path**: `discounts/apply/`
- **View**: `apply_discount_via_referrer`
- **Score**: 6/10 (USEFUL)
- **Notes**: Useful - discount system

### social_media_dashboard
- **Path**: `social-media/`
- **View**: `views.social_media_dashboard`
- **Score**: 3/10 (OPTIONAL)
- **Notes**: Optional - social media dashboard

### post_to_twitter
- **Path**: `social-media/post/<int:post_id>/`
- **View**: `views.post_to_twitter`
- **Score**: 3/10 (OPTIONAL)
- **Notes**: Optional - post to twitter

### create_scheduled_post
- **Path**: `social-media/create/`
- **View**: `views.create_scheduled_post`
- **Score**: 3/10 (OPTIONAL)
- **Notes**: Optional - schedule post

### gsoc_landing_page
- **Path**: `gsoc/`
- **View**: `views.gsoc_landing_page`
- **Score**: 3/10 (OPTIONAL)
- **Notes**: Optional - GSoC page

### delete_post
- **Path**: `social-media/delete/<int:post_id>/`
- **View**: `views.delete_post`
- **Score**: 2/10 (OPTIONAL)
- **Notes**: Optional - delete post

## Merchandise

### storefront_create
- **Path**: `store/create/`
- **View**: `views.StorefrontCreateView`
- **Score**: 4/10 (OPTIONAL)
- **Notes**: Optional - create store

### storefront_update
- **Path**: `store/<slug:store_slug>/edit/`
- **View**: `views.StorefrontUpdateView`
- **Score**: 4/10 (OPTIONAL)
- **Notes**: Optional - edit store

### storefront_detail
- **Path**: `storefront/<slug:store_slug>/`
- **View**: `views.StorefrontDetailView`
- **Score**: 4/10 (OPTIONAL)
- **Notes**: Optional - store detail

### goods_list
- **Path**: `goods/`
- **View**: `views.GoodsListView`
- **Score**: 4/10 (OPTIONAL)
- **Notes**: Optional - goods list

### goods_detail
- **Path**: `goods/<int:pk>/`
- **View**: `views.GoodsDetailView`
- **Score**: 4/10 (OPTIONAL)
- **Notes**: Optional - goods detail

### goods_create
- **Path**: `store/<slug:store_slug>/goods/create/`
- **View**: `views.GoodsCreateView`
- **Score**: 4/10 (OPTIONAL)
- **Notes**: Optional - create goods

### add_goods_to_cart
- **Path**: `goods/add-to-cart/<int:pk>/`
- **View**: `add_goods_to_cart`
- **Score**: 4/10 (OPTIONAL)
- **Notes**: Optional - add goods to cart

### goods_listing
- **Path**: `products/`
- **View**: `GoodsListingView`
- **Score**: 4/10 (OPTIONAL)
- **Notes**: Optional - products listing

### order_detail
- **Path**: `orders/<int:pk>/`
- **View**: `views.OrderDetailView`
- **Score**: 4/10 (OPTIONAL)
- **Notes**: Optional - order detail

### store_order_management
- **Path**: `store/<slug:store_slug>/orders/`
- **View**: `views.OrderManagementView`
- **Score**: 4/10 (OPTIONAL)
- **Notes**: Optional - order management

### update_order_status
- **Path**: `orders/item/<int:item_id>/update-status/`
- **View**: `views.update_order_status`
- **Score**: 4/10 (OPTIONAL)
- **Notes**: Optional - update order

### goods_update
- **Path**: `goods/<int:pk>/edit/`
- **View**: `views.GoodsUpdateView`
- **Score**: 3/10 (OPTIONAL)
- **Notes**: Optional - edit goods

### goods_delete
- **Path**: `goods/delete/<int:pk>/`
- **View**: `views.GoodsDeleteView`
- **Score**: 3/10 (OPTIONAL)
- **Notes**: Optional - delete goods

### store_analytics
- **Path**: `store/<slug:store_slug>/analytics/`
- **View**: `views.StoreAnalyticsView`
- **Score**: 3/10 (OPTIONAL)
- **Notes**: Optional - store analytics

### admin_merch_analytics
- **Path**: `admin/merchandise-analytics/`
- **View**: `views.AdminMerchAnalyticsView`
- **Score**: 3/10 (OPTIONAL)
- **Notes**: Optional - admin merch analytics

## Payments

### create_payment_intent
- **Path**: `courses/<slug:slug>/create-payment-intent/`
- **View**: `views.create_payment_intent`
- **Score**: 10/10 (CRITICAL)
- **Notes**: Critical - course payments

### stripe_webhook
- **Path**: `stripe-webhook/`
- **View**: `views.stripe_webhook`
- **Score**: 10/10 (CRITICAL)
- **Notes**: Critical - payment processing

### cart_view
- **Path**: `cart/`
- **View**: `views.cart_view`
- **Score**: 9/10 (CRITICAL)
- **Notes**: Critical - shopping cart

### add_course_to_cart
- **Path**: `cart/add/course/<int:course_id>/`
- **View**: `views.add_course_to_cart`
- **Score**: 9/10 (CRITICAL)
- **Notes**: Critical - add to cart

### create_cart_payment_intent
- **Path**: `cart/payment-intent/`
- **View**: `views.create_cart_payment_intent`
- **Score**: 9/10 (CRITICAL)
- **Notes**: Critical - checkout

### checkout_success
- **Path**: `cart/checkout/success/`
- **View**: `views.checkout_success`
- **Score**: 9/10 (CRITICAL)
- **Notes**: Critical - payment confirmation

### stripe_connect_onboarding
- **Path**: `stripe/connect/onboarding/`
- **View**: `views.stripe_connect_onboarding`
- **Score**: 8/10 (IMPORTANT)
- **Notes**: Important - teacher payouts

### stripe_connect_webhook
- **Path**: `stripe/connect/webhook/`
- **View**: `views.stripe_connect_webhook`
- **Score**: 8/10 (IMPORTANT)
- **Notes**: Important - teacher payouts

### add_session_to_cart
- **Path**: `cart/add/session/<int:session_id>/`
- **View**: `views.add_session_to_cart`
- **Score**: 8/10 (IMPORTANT)
- **Notes**: Important - session purchase

### remove_from_cart
- **Path**: `cart/remove/<int:item_id>/`
- **View**: `views.remove_from_cart`
- **Score**: 8/10 (IMPORTANT)
- **Notes**: Important - cart management

### membership_checkout
- **Path**: `membership/checkout/<int:plan_id>/`
- **View**: `views.membership_checkout`
- **Score**: 7/10 (IMPORTANT)
- **Notes**: Important - membership checkout

### create_membership_subscription
- **Path**: `membership/create-subscription/`
- **View**: `views.create_membership_subscription`
- **Score**: 7/10 (IMPORTANT)
- **Notes**: Important - membership creation

### membership_settings
- **Path**: `membership/settings/`
- **View**: `views.membership_settings`
- **Score**: 7/10 (IMPORTANT)
- **Notes**: Important - membership management

### donate
- **Path**: `donate/`
- **View**: `views.donate`
- **Score**: 6/10 (USEFUL)
- **Notes**: Useful - donation page

### create_donation_payment_intent
- **Path**: `donate/payment-intent/`
- **View**: `views.create_donation_payment_intent`
- **Score**: 6/10 (USEFUL)
- **Notes**: Useful - donations

### membership_success
- **Path**: `membership/success/`
- **View**: `views.membership_success`
- **Score**: 6/10 (USEFUL)
- **Notes**: Useful - membership success

### cancel_membership
- **Path**: `membership/cancel/`
- **View**: `views.cancel_membership`
- **Score**: 6/10 (USEFUL)
- **Notes**: Useful - membership cancel

### update_payment_method
- **Path**: `membership/update-payment-method/`
- **View**: `views.update_payment_method`
- **Score**: 6/10 (USEFUL)
- **Notes**: Useful - payment updates

### update_payment_method_api
- **Path**: `membership/update-payment-method/api/`
- **View**: `views.update_payment_method_api`
- **Score**: 6/10 (USEFUL)
- **Notes**: Useful - payment API

### create_donation_subscription
- **Path**: `donate/subscription/`
- **View**: `views.create_donation_subscription`
- **Score**: 5/10 (USEFUL)
- **Notes**: Useful - recurring donations

### donation_success
- **Path**: `donate/success/`
- **View**: `views.donation_success`
- **Score**: 5/10 (USEFUL)
- **Notes**: Useful - donation success

### donation_cancel
- **Path**: `donate/cancel/`
- **View**: `views.donation_cancel`
- **Score**: 5/10 (USEFUL)
- **Notes**: Useful - donation cancel

### donation_webhook
- **Path**: `donate/webhook/`
- **View**: `views.donation_webhook`
- **Score**: 5/10 (USEFUL)
- **Notes**: Useful - donation webhook

### reactivate_membership
- **Path**: `membership/reactivate/`
- **View**: `views.reactivate_membership`
- **Score**: 5/10 (USEFUL)
- **Notes**: Useful - membership reactivate

## Personalization

### customize_avatar
- **Path**: `avatar/customize/`
- **View**: `views_avatar.customize_avatar`
- **Score**: 4/10 (OPTIONAL)
- **Notes**: Optional - avatar customize

### set_avatar_as_profile_pic
- **Path**: `avatar/set-as-profile/`
- **View**: `views_avatar.set_avatar_as_profile_pic`
- **Score**: 3/10 (OPTIONAL)
- **Notes**: Optional - set profile pic

### preview_avatar
- **Path**: `avatar/preview/`
- **View**: `views_avatar.preview_avatar`
- **Score**: 3/10 (OPTIONAL)
- **Notes**: Optional - avatar preview

## Progress

### mark_session_attendance
- **Path**: `sessions/<int:session_id>/attendance/`
- **View**: `views.mark_session_attendance`
- **Score**: 9/10 (CRITICAL)
- **Notes**: Critical - attendance tracking

### mark_session_completed
- **Path**: `sessions/<int:session_id>/complete/`
- **View**: `views.mark_session_completed`
- **Score**: 9/10 (CRITICAL)
- **Notes**: Critical - session completion

### student_progress
- **Path**: `enrollment/<int:enrollment_id>/progress/`
- **View**: `views.student_progress`
- **Score**: 8/10 (IMPORTANT)
- **Notes**: Important - student progress

### course_progress_overview
- **Path**: `courses/<slug:slug>/progress/`
- **View**: `views.course_progress_overview`
- **Score**: 7/10 (IMPORTANT)
- **Notes**: Useful - course overview

### update_student_progress
- **Path**: `enrollment/<int:enrollment_id>/update-progress/`
- **View**: `views.update_student_progress`
- **Score**: 7/10 (IMPORTANT)
- **Notes**: Important - progress updates

### certificate_detail
- **Path**: `certificate/<uuid:certificate_id>/`
- **View**: `views.certificate_detail`
- **Score**: 7/10 (IMPORTANT)
- **Notes**: Important - certificate display

### generate_certificate
- **Path**: `certificate/generate/<int:enrollment_id>/`
- **View**: `views.generate_certificate`
- **Score**: 7/10 (IMPORTANT)
- **Notes**: Important - certificate generation

### update_teacher_notes
- **Path**: `enrollment/<int:enrollment_id>/update-notes/`
- **View**: `views.update_teacher_notes`
- **Score**: 6/10 (USEFUL)
- **Notes**: Useful - teacher notes

## Scheduling

### calendar_feed
- **Path**: `calendar/feed/`
- **View**: `views.calendar_feed`
- **Score**: 7/10 (IMPORTANT)
- **Notes**: Important - calendar feed

### calendar_links
- **Path**: `calendar/session/<int:session_id>/`
- **View**: `views.calendar_links`
- **Score**: 7/10 (IMPORTANT)
- **Notes**: Important - session calendar

### course_calendar
- **Path**: `courses/<slug:slug>/calendar/`
- **View**: `views.get_course_calendar`
- **Score**: 7/10 (IMPORTANT)
- **Notes**: Important - course calendar

### create_calendar
- **Path**: `calendar/create/`
- **View**: `views.create_calendar`
- **Score**: 5/10 (USEFUL)
- **Notes**: Useful - calendar creation

### view_calendar
- **Path**: `calendar/<str:share_token>/`
- **View**: `views.view_calendar`
- **Score**: 5/10 (USEFUL)
- **Notes**: Useful - view calendar

### get_calendar_data
- **Path**: `calendar/<str:share_token>/data`
- **View**: `views.get_calendar_data`
- **Score**: 5/10 (USEFUL)
- **Notes**: Useful - calendar data

### add_time_slot
- **Path**: `calendar/<str:share_token>/add-slot`
- **View**: `views.add_time_slot`
- **Score**: 4/10 (OPTIONAL)
- **Notes**: Optional - add time slot

### remove_time_slot
- **Path**: `calendar/<str:share_token>/remove-slot`
- **View**: `views.remove_time_slot`
- **Score**: 4/10 (OPTIONAL)
- **Notes**: Optional - remove time slot

## Social

### public_profile
- **Path**: `profile/<str:username>/`
- **View**: `views.public_profile`
- **Score**: 7/10 (IMPORTANT)
- **Notes**: Important - public profiles

### users_list
- **Path**: `users/`
- **View**: `views.users_list`
- **Score**: 6/10 (USEFUL)
- **Notes**: Useful - user list

### contributors_list_view
- **Path**: `contributors/`
- **View**: `views.contributors_list_view`
- **Score**: 4/10 (OPTIONAL)
- **Notes**: Optional - contributors

### contributor_detail
- **Path**: `contributors/<str:username>/`
- **View**: `views.contributor_detail_view`
- **Score**: 3/10 (OPTIONAL)
- **Notes**: Optional - contributor detail

## Tools

### tracker_list
- **Path**: `trackers/`
- **View**: `views.tracker_list`
- **Score**: 4/10 (OPTIONAL)
- **Notes**: Optional - tracker list

### create_tracker
- **Path**: `trackers/create/`
- **View**: `views.create_tracker`
- **Score**: 4/10 (OPTIONAL)
- **Notes**: Optional - create tracker

### tracker_detail
- **Path**: `trackers/<int:tracker_id>/`
- **View**: `views.tracker_detail`
- **Score**: 4/10 (OPTIONAL)
- **Notes**: Optional - tracker detail

### update_tracker
- **Path**: `trackers/<int:tracker_id>/update/`
- **View**: `views.update_tracker`
- **Score**: 4/10 (OPTIONAL)
- **Notes**: Optional - update tracker

### update_progress
- **Path**: `trackers/<int:tracker_id>/progress/`
- **View**: `views.update_progress`
- **Score**: 4/10 (OPTIONAL)
- **Notes**: Optional - update progress

### graphing_calculator
- **Path**: `graphing_calculator/`
- **View**: `views.graphing_calculator`
- **Score**: 4/10 (OPTIONAL)
- **Notes**: Optional - graphing calculator

### embed_tracker
- **Path**: `trackers/embed/<str:embed_code>/`
- **View**: `views.embed_tracker`
- **Score**: 3/10 (OPTIONAL)
- **Notes**: Optional - embed tracker

## Virtual Classroom

### virtual_classroom_list
- **Path**: `virtual-classroom/`
- **View**: `views.virtual_classroom_list`
- **Score**: 7/10 (IMPORTANT)
- **Notes**: Important - classroom list

### virtual_classroom_create
- **Path**: `virtual-classroom/create/`
- **View**: `views.virtual_classroom_create`
- **Score**: 7/10 (IMPORTANT)
- **Notes**: Important - classroom creation

### virtual_classroom_detail
- **Path**: `virtual-classroom/<int:classroom_id>/`
- **View**: `views.virtual_classroom_detail`
- **Score**: 7/10 (IMPORTANT)
- **Notes**: Important - classroom detail

### classroom_attendance
- **Path**: `virtual-classroom/<int:classroom_id>/attendance/`
- **View**: `classroom_attendance`
- **Score**: 7/10 (IMPORTANT)
- **Notes**: Important - attendance

### update_student_attendance
- **Path**: `attendance/<int:classroom_id>/update/`
- **View**: `update_student_attendance`
- **Score**: 7/10 (IMPORTANT)
- **Notes**: Important - update attendance

### join_global_virtual_classroom
- **Path**: `virtual-classroom/global/join/`
- **View**: `views.join_global_virtual_classroom`
- **Score**: 6/10 (USEFUL)
- **Notes**: Useful - global classroom

### virtual_classroom_edit
- **Path**: `virtual-classroom/<int:classroom_id>/edit/`
- **View**: `views.virtual_classroom_edit`
- **Score**: 6/10 (USEFUL)
- **Notes**: Useful - classroom edit

### classroom_blackboard
- **Path**: `virtual-classroom/<int:classroom_id>/blackboard/`
- **View**: `views.classroom_blackboard`
- **Score**: 6/10 (USEFUL)
- **Notes**: Useful - blackboard

### classroom_whiteboard
- **Path**: `virtual-classroom/<int:classroom_id>/whiteboard/`
- **View**: `views_whiteboard.classroom_whiteboard`
- **Score**: 6/10 (USEFUL)
- **Notes**: Useful - whiteboard

### virtual_lab
- **Path**: `virtual_lab/`
- **View**: `web.virtual_lab.urls`
- **Score**: 6/10 (USEFUL)
- **Notes**: Useful - virtual lab

### virtual_classroom_delete
- **Path**: `virtual-classroom/<int:classroom_id>/delete/`
- **View**: `views.virtual_classroom_delete`
- **Score**: 5/10 (USEFUL)
- **Notes**: Useful - classroom delete

### get_whiteboard_data
- **Path**: `virtual-classroom/<int:classroom_id>/whiteboard/data/`
- **View**: `views_whiteboard.get_whiteboard_data`
- **Score**: 5/10 (USEFUL)
- **Notes**: Useful - whiteboard data

### save_whiteboard_data
- **Path**: `virtual-classroom/<int:classroom_id>/whiteboard/save/`
- **View**: `views_whiteboard.save_whiteboard_data`
- **Score**: 5/10 (USEFUL)
- **Notes**: Useful - save whiteboard

### whiteboard
- **Path**: `whiteboard/`
- **View**: `views.whiteboard`
- **Score**: 5/10 (USEFUL)
- **Notes**: Useful - standalone whiteboard

### virtual_classroom_customize
- **Path**: `virtual-classroom/<int:classroom_id>/customize/`
- **View**: `views.virtual_classroom_customize`
- **Score**: 4/10 (OPTIONAL)
- **Notes**: Optional - classroom customize

### reset_attendance
- **Path**: `virtual-classroom/<int:classroom_id>/reset-attendance/`
- **View**: `views.reset_attendance`
- **Score**: 4/10 (OPTIONAL)
- **Notes**: Optional - reset attendance

### clear_whiteboard
- **Path**: `virtual-classroom/<int:classroom_id>/whiteboard/clear/`
- **View**: `views_whiteboard.clear_whiteboard`
- **Score**: 4/10 (OPTIONAL)
- **Notes**: Optional - clear whiteboard

---

## Recommendations

### Critical Endpoints (Score 9-10)
These endpoints are essential to the platform and should NEVER be removed:

- `i18n` (10/10): Critical - language selection
- `index` (10/10): Critical - homepage
- `learn` (10/10): Critical - main student entry point
- `teach` (10/10): Critical - main teacher entry point
- `account_signup` (10/10): Critical - user registration
- `accounts` (10/10): Critical - login/logout/auth
- `student_dashboard` (10/10): Critical - main student dashboard
- `teacher_dashboard` (10/10): Critical - main teacher dashboard
- `create_course` (10/10): Critical - course creation
- `course_detail` (10/10): Critical - course detail view
- `enroll_course` (10/10): Critical - course enrollment
- `create_payment_intent` (10/10): Critical - course payments
- `stripe_webhook` (10/10): Critical - payment processing
- `admin` (10/10): Critical - Django admin
- `captcha` (9/10): Critical - security/anti-spam
- `profile` (9/10): Critical - user profile management
- `accounts_profile` (9/10): Critical - user profile
- `course_search` (9/10): Critical - course discovery
- `update_course` (9/10): Critical - course management
- `add_session` (9/10): Critical - session creation
- `mark_session_attendance` (9/10): Critical - attendance tracking
- `mark_session_completed` (9/10): Critical - session completion
- `cart_view` (9/10): Critical - shopping cart
- `add_course_to_cart` (9/10): Critical - add to cart
- `create_cart_payment_intent` (9/10): Critical - checkout
- `checkout_success` (9/10): Critical - payment confirmation
- `take_quiz` (9/10): Critical - quiz taking
- `admin_dashboard` (9/10): Critical - admin dashboard

### Important Endpoints (Score 7-8)
These endpoints are important to core functionality. Remove with caution:

- `about` (8/10): Important - site information
- `terms` (8/10): Important - legal
- `delete_course` (8/10): Important - course deletion
- `toggle_course_status` (8/10): Important - course status
- `edit_session` (8/10): Important - session editing
- `session_detail` (8/10): Important - session detail
- `message_students` (8/10): Important - student communication
- `upload_material` (8/10): Important - course materials
- `download_material` (8/10): Important - material access
- `student_progress` (8/10): Important - student progress
- `stripe_connect_onboarding` (8/10): Important - teacher payouts
- `stripe_connect_webhook` (8/10): Important - teacher payouts
- `add_session_to_cart` (8/10): Important - session purchase
- `remove_from_cart` (8/10): Important - cart management
- `messaging_dashboard` (8/10): Important - messaging hub
- `compose_message` (8/10): Important - message composition
- `inbox` (8/10): Important - message inbox
- `quiz_list` (8/10): Important - quiz listing
- `create_quiz` (8/10): Important - quiz creation
- `quiz_detail` (8/10): Important - quiz detail
- `add_question` (8/10): Important - question creation
- `quiz_results` (8/10): Important - quiz results
- `system_dashboard` (8/10): Important - system dashboard
- `markdownx` (7/10): Important - content editing
- `system_status` (7/10): Important - system status
- `feedback` (7/10): Important - user feedback
- `delete_account` (7/10): Important - account deletion
- `notification_preferences` (7/10): Important - notifications
- `content_dashboard` (7/10): Useful - content creator dashboard
- `progress_visualization` (7/10): Useful - progress tracking
- `add_student_to_course` (7/10): Important - manual enrollment
- `student_management` (7/10): Important - student management
- `message_teacher` (7/10): Important - teacher communication
- `course_analytics` (7/10): Useful - course insights
- `delete_material` (7/10): Important - material management
- `add_review` (7/10): Important - reviews
- `course_progress_overview` (7/10): Useful - course overview
- `update_student_progress` (7/10): Important - progress updates
- `certificate_detail` (7/10): Important - certificate display
- `generate_certificate` (7/10): Important - certificate generation
- `membership_checkout` (7/10): Important - membership checkout
- `create_membership_subscription` (7/10): Important - membership creation
- `membership_settings` (7/10): Important - membership management
- `send_encrypted_message` (7/10): Important - secure messaging
- `forum_categories` (7/10): Important - forum home
- `forum_category` (7/10): Important - forum category
- `create_topic` (7/10): Important - topic creation
- `forum_topic` (7/10): Important - topic view
- `update_quiz` (7/10): Important - quiz editing
- `edit_question` (7/10): Important - question editing
- `quiz_take_shared` (7/10): Important - shared quizzes
- `grade_short_answer` (7/10): Important - manual grading
- `blog_list` (7/10): Important - blog listing
- `blog_detail` (7/10): Important - blog post
- `public_profile` (7/10): Important - public profiles
- `calendar_feed` (7/10): Important - calendar feed
- `calendar_links` (7/10): Important - session calendar
- `course_calendar` (7/10): Important - course calendar
- `virtual_classroom_list` (7/10): Important - classroom list
- `virtual_classroom_create` (7/10): Important - classroom creation
- `virtual_classroom_detail` (7/10): Important - classroom detail
- `classroom_attendance` (7/10): Important - attendance
- `update_student_attendance` (7/10): Important - update attendance
- `system_metrics_api` (7/10): Important - metrics API

### Optional/Removable Endpoints (Score 1-4)
These endpoints could be removed or deprecated with minimal impact:

- `delete_post` (2/10): Optional - delete post
- `add_meme` (2/10): Optional - add meme
- `meme_detail` (2/10): Optional - meme detail
- `test_sentry` (2/10): Optional - sentry testing
- `classroom_whiteboard_legacy` (2/10): Deprecated - legacy redirect
- `update_student_attendance_legacy` (2/10): Deprecated - legacy redirect
- `sync_github_milestones` (3/10): Optional - GitHub sync
- `social_media_dashboard` (3/10): Optional - social media dashboard
- `post_to_twitter` (3/10): Optional - post to twitter
- `create_scheduled_post` (3/10): Optional - schedule post
- `gsoc_landing_page` (3/10): Optional - GSoC page
- `sync_github_milestones` (3/10): Optional - GitHub integration
- `leave_session_waiting_room` (3/10): Optional - session waiting
- `fetch_video_title` (3/10): Optional - video metadata
- `meme_list` (3/10): Optional - meme list
- `contributor_detail` (3/10): Optional - contributor detail
- `embed_tracker` (3/10): Optional - embed tracker
- `set_avatar_as_profile_pic` (3/10): Optional - set profile pic
- `preview_avatar` (3/10): Optional - avatar preview
- `goods_update` (3/10): Optional - edit goods
- `goods_delete` (3/10): Optional - delete goods
- `store_analytics` (3/10): Optional - store analytics
- `admin_merch_analytics` (3/10): Optional - admin merch analytics
- `add_featured_review` (4/10): Optional - featured reviews
- `remove_featured_review` (4/10): Optional - featured reviews
- `toggle_star_message` (4/10): Optional - star messages
- `leave_waiting_room` (4/10): Optional - leave waiting room
- `delete_waiting_room` (4/10): Optional - delete waiting room
- `join_session_waiting_room` (4/10): Optional - session waiting
- `accept_invitation` (4/10): Optional - challenge accept
- `decline_invitation` (4/10): Optional - challenge decline
- `challenge_leaderboard` (4/10): Optional - leaderboard
- `submit_to_leaderboard` (4/10): Optional - leaderboard submit
- `current_weekly_challenge` (4/10): Optional - weekly challenge
- `survey-delete` (4/10): Optional - survey deletion
- `feature_vote` (4/10): Optional - vote feature
- `feature_vote_count` (4/10): Optional - vote count
- `edit_success_story` (4/10): Optional - edit story
- `delete_success_story` (4/10): Optional - delete story
- `video_request_list` (4/10): Optional - video requests
- `submit_video_request` (4/10): Optional - submit request
- `contributors_list_view` (4/10): Optional - contributors
- `add_time_slot` (4/10): Optional - add time slot
- `remove_time_slot` (4/10): Optional - remove time slot
- `virtual_classroom_customize` (4/10): Optional - classroom customize
- `reset_attendance` (4/10): Optional - reset attendance
- `clear_whiteboard` (4/10): Optional - clear whiteboard
- `accept_team_invite` (4/10): Optional - accept invite
- `decline_team_invite` (4/10): Optional - decline invite
- `delete_team_goal` (4/10): Optional - delete goal
- `remove_team_member` (4/10): Optional - remove member
- `edit_team_goal` (4/10): Optional - edit goal
- `submit_team_proof` (4/10): Optional - submit proof
- `tracker_list` (4/10): Optional - tracker list
- `create_tracker` (4/10): Optional - create tracker
- `tracker_detail` (4/10): Optional - tracker detail
- `update_tracker` (4/10): Optional - update tracker
- `update_progress` (4/10): Optional - update progress
- `graphing_calculator` (4/10): Optional - graphing calculator
- `customize_avatar` (4/10): Optional - avatar customize
- `storefront_create` (4/10): Optional - create store
- `storefront_update` (4/10): Optional - edit store
- `storefront_detail` (4/10): Optional - store detail
- `goods_list` (4/10): Optional - goods list
- `goods_detail` (4/10): Optional - goods detail
- `goods_create` (4/10): Optional - create goods
- `add_goods_to_cart` (4/10): Optional - add goods to cart
- `goods_listing` (4/10): Optional - products listing
- `order_detail` (4/10): Optional - order detail
- `store_order_management` (4/10): Optional - order management
- `update_order_status` (4/10): Optional - update order
- `classes_map` (4/10): Optional - classes map
- `map_data_api` (4/10): Optional - map data API

---

## Feature Reduction Recommendations

### High Priority for Removal/Consolidation

1. **Memes Feature** (Score: 2-3)
   - Low educational value
   - Not core to platform mission
   - Endpoints: `memes/`, `memes/add/`, `memes/<slug>/`

2. **Social Media Management** (Score: 2-3)
   - Better handled by external tools
   - Not core to education platform
   - Endpoints: All `social-media/*` endpoints

3. **Legacy Redirects** (Score: 2)
   - Can be removed after sufficient migration period
   - Endpoints: `whiteboard/<int>/`, `update_student_attendance/<int>/`

4. **Merchandise System** (Score: 3-4)
   - Complex feature with low educational value
   - Consider simplifying or removing
   - All storefront and goods management endpoints

5. **Team Goals/Collaboration** (Score: 4-5)
   - Overlaps with study groups
   - Consider consolidating features
   - All `teams/*` endpoints

6. **Trackers** (Score: 3-4)
   - Niche feature with limited usage
   - Consider removing if analytics show low adoption
   - All `trackers/*` endpoints

7. **Waiting Rooms** (Score: 4-5)
   - Complex feature, unclear value proposition
   - May overlap with course enrollment
   - Consider simplifying or removing

### Medium Priority for Review

1. **Multiple Calendar Systems**
   - Multiple calendar endpoints suggest fragmentation
   - Consider consolidating calendar features

2. **Peer Challenges**
   - Good concept but may have low adoption
   - Monitor usage before deciding

3. **Avatar Customization**
   - Nice-to-have feature
   - Low priority for educational platform

