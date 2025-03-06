-- Database schema for AI Interview Prep application

-- Users table
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT TRUE,
    is_admin BOOLEAN DEFAULT FALSE,
    auth0_id VARCHAR(255) UNIQUE
);

-- Subscription plans table
CREATE TABLE subscription_plans (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    price_monthly DECIMAL(10, 2) NOT NULL,
    price_yearly DECIMAL(10, 2) NOT NULL,
    stripe_price_id_monthly VARCHAR(100) NOT NULL,
    stripe_price_id_yearly VARCHAR(100) NOT NULL,
    features JSONB NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- User subscriptions table
CREATE TABLE user_subscriptions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    subscription_plan_id INTEGER NOT NULL REFERENCES subscription_plans(id),
    stripe_customer_id VARCHAR(100) NOT NULL,
    stripe_subscription_id VARCHAR(100) NOT NULL,
    status VARCHAR(50) NOT NULL, -- 'active', 'canceled', 'past_due', 'trialing', etc.
    current_period_start TIMESTAMP WITH TIME ZONE NOT NULL,
    current_period_end TIMESTAMP WITH TIME ZONE NOT NULL,
    cancel_at_period_end BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, subscription_plan_id)
);

-- Payment history table
CREATE TABLE payment_history (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    subscription_id INTEGER REFERENCES user_subscriptions(id) ON DELETE SET NULL,
    stripe_payment_intent_id VARCHAR(100) NOT NULL,
    amount DECIMAL(10, 2) NOT NULL,
    currency VARCHAR(3) NOT NULL DEFAULT 'USD',
    status VARCHAR(50) NOT NULL, -- 'succeeded', 'processing', 'failed', etc.
    payment_method_type VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Interview sessions table (extended to include subscription info)
CREATE TABLE interview_sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    job_title VARCHAR(255) NOT NULL,
    job_description TEXT,
    cv_text TEXT,
    interview_type VARCHAR(50) NOT NULL,
    duration INTEGER NOT NULL,
    questions JSONB,
    answers JSONB,
    feedback JSONB,
    score INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE
);

-- Feature usage tracking
CREATE TABLE feature_usage (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    feature_name VARCHAR(100) NOT NULL,
    usage_count INTEGER DEFAULT 1,
    last_used_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Initial data for subscription plans
INSERT INTO subscription_plans (name, description, price_monthly, price_yearly, stripe_price_id_monthly, stripe_price_id_yearly, features, is_active)
VALUES 
('Free', 'Basic interview preparation with limited features', 0.00, 0.00, 'price_free_monthly', 'price_free_yearly', 
 '{"interviews_per_month": 2, "feedback_detail": "basic", "interview_duration_max": 15, "code_challenges": false, "video_interviews": false}'::jsonb, 
 true),
 
('Basic', 'Enhanced interview preparation with more features', 9.99, 99.99, 'price_basic_monthly', 'price_basic_yearly', 
 '{"interviews_per_month": 10, "feedback_detail": "detailed", "interview_duration_max": 30, "code_challenges": true, "video_interviews": false}'::jsonb, 
 true),
 
('Premium', 'Comprehensive interview preparation with all features', 19.99, 199.99, 'price_premium_monthly', 'price_premium_yearly', 
 '{"interviews_per_month": -1, "feedback_detail": "comprehensive", "interview_duration_max": 60, "code_challenges": true, "video_interviews": true}'::jsonb, 
 true);

-- Indexes for performance
CREATE INDEX idx_user_subscriptions_user_id ON user_subscriptions(user_id);
CREATE INDEX idx_interview_sessions_user_id ON interview_sessions(user_id);
CREATE INDEX idx_payment_history_user_id ON payment_history(user_id);
CREATE INDEX idx_feature_usage_user_id ON feature_usage(user_id); 