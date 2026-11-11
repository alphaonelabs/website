-- Migration: add allow_buddy_requests column to user_profiles
-- Defaults to 0 (unchecked). Only users who enable this can receive study buddy requests.
ALTER TABLE user_profiles ADD COLUMN allow_buddy_requests INTEGER NOT NULL DEFAULT 0;
