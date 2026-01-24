# Persistent Storage Solutions for Streamlit Cloud

Streamlit Cloud's file system is **ephemeral** - files don't persist across app restarts. Here are solutions:

## Option 1: Supabase (Recommended - Free)
A PostgreSQL database with built-in auth and storage.

### Setup:
1. Go to https://supabase.com and create a free project
2. Create a table `users` with columns:
   - `username` (text, primary key)
   - `password` (text)
   - `is_admin` (boolean)

3. Get your credentials:
   - Project URL
   - Anon Key

4. In Streamlit Cloud app settings, add secrets:
   ```
   SUPABASE_URL = "your-project-url"
   SUPABASE_KEY = "your-anon-key"
   ```

5. Update `utils/auth.py` to use Supabase instead of CSV

## Option 2: Firebase (Free tier available)
Google's real-time database.

## Option 3: Use Streamlit Secrets + CSV
Store CSV content in Streamlit Cloud secrets (not ideal for large data).

## Current Workaround:
The app now has **"First Time Setup"** - when the database is cleared, you can recreate the admin account.

**For now:** Every time the app restarts, use the setup page to recreate your admin account.

## Recommendation:
For a production app with 10 users, switch to **Supabase** for ~$0-5/month. Let me know if you want me to implement Supabase integration!
