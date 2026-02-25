# Supabase Setup Guide

## Step 1: Create a Supabase Project

1. Go to https://supabase.com
2. Click **"Sign up"** (use email/GitHub)
3. Create a new project (free tier is fine)
4. Wait for it to initialize (~2 minutes)

## Step 2: Create the Users Table

1. In Supabase dashboard, go to **"SQL Editor"** (left sidebar)
2. Click **"New Query"**
3. Copy and paste this:

```sql
CREATE TABLE users (
  id BIGSERIAL PRIMARY KEY,
  username TEXT UNIQUE NOT NULL,
  password TEXT NOT NULL,
  is_admin BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMP DEFAULT NOW()
);
```

4. Click **"Run"**

## Step 3: Get Your Credentials

1. Go to **"Settings"** (bottom left)
2. Click **"API"**
3. Copy:
   - **Project URL** (e.g., `https://xxx.supabase.co`)
   - **Anon Key** (under "anon public")

## Step 4: Add to Streamlit Cloud

1. Go to your Streamlit Cloud app settings
2. Click **"Secrets"**
3. Add these two lines:

```
SUPABASE_URL = "paste-your-project-url-here"
SUPABASE_KEY = "paste-your-anon-key-here"
```

4. Click **"Save"**
5. Your app will auto-redeploy

## Step 5: Test

1. Go to your app URL
2. Register an account - **the first user will be admin automatically**
3. Login and enjoy persistent data!

## Done! ✅

Your data now persists forever. No more losing users when the app restarts!

### Notes:
- Free Supabase tier has 500MB storage + unlimited reads/writes
- Perfect for your team of 10 people
- Data is encrypted and secure

## Optional: Enable "Remember this device"

To persist login across app sleep/wake, run the SQL in:

`ADD_AUTH_SESSIONS_TABLE.sql`

This is an additive migration and does not delete or reset existing data.
