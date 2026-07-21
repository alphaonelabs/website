-- Migration 0008: Referral program lookup support.

ALTER TABLE user_profiles ADD COLUMN referral_code_hash TEXT;

CREATE INDEX IF NOT EXISTS idx_user_profiles_referral_code_hash
    ON user_profiles(referral_code_hash);

CREATE INDEX IF NOT EXISTS idx_user_profiles_referred_by
    ON user_profiles(referred_by_user_id);
