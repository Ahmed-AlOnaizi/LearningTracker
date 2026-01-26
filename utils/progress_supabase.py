import streamlit as st
from utils.auth import supabase, USE_SUPABASE
from datetime import datetime

def get_user_progress(username):
    """Get all progress records for a specific user"""
    if not USE_SUPABASE:
        st.error("Supabase not initialized")
        return []
    try:
        response = supabase.table("user_progress").select("*").eq("username", username).execute()
        # Normalize column names to match app expectations (Course, Progress %, Status, Notes)
        normalized_data = []
        for row in response.data:
            normalized_data.append({
                'username': row.get('username'),
                'Course': row.get('course', ''),
                'Progress %': row.get('progress_percent', 0),
                'Status': row.get('status', 'In Progress'),
                'Notes': row.get('notes', '')
            })
        return normalized_data
    except Exception as e:
        st.error(f"Database error in get_user_progress: {type(e).__name__}: {e}")
        return []

def get_all_progress():
    """Get all progress records for all users"""
    if not USE_SUPABASE:
        st.error("Supabase not initialized")
        return []
    try:
        response = supabase.table("user_progress").select("*").execute()
        # Normalize column names to match app expectations
        normalized_data = []
        for row in response.data:
            normalized_data.append({
                'username': row.get('username'),
                'Course': row.get('course', ''),
                'Progress %': row.get('progress_percent', 0),
                'Status': row.get('status', 'In Progress'),
                'Notes': row.get('notes', ''),
                'Last Updated': row.get('updated_at', '')
            })
        return normalized_data
    except Exception as e:
        st.error(f"Database error in get_all_progress: {type(e).__name__}: {e}")
        return []

def upsert_user_progress(progress_dict):
    """Insert or update user progress record. Uses lowercase column names matching Supabase."""
    if not USE_SUPABASE:
        st.error("Supabase not initialized")
        return False
    try:
        # Map to exact Supabase column names (all lowercase with underscores)
        supa_dict = {
            "username": progress_dict.get("username"),
            "course": progress_dict.get("Course"),
            "progress_percent": int(progress_dict.get("Progress %", 0)),
            "status": progress_dict.get("Status", "In Progress"),
            "notes": progress_dict.get("Notes", ""),
            "updated_at": datetime.now().isoformat()
        }
        # Upsert: insert if new, update if exists (based on username + course unique constraint)
        response = supabase.table("user_progress").upsert(supa_dict, on_conflict="username,course").execute()
        return True
    except Exception as e:
        st.error(f"Database error in upsert_user_progress: {type(e).__name__}: {e}")
        return False

def delete_user_progress(username, course):
    """Delete a progress record"""
    if not USE_SUPABASE:
        st.error("Supabase not initialized")
        return False
    try:
        response = supabase.table("user_progress").delete().eq("username", username).eq("course", course).execute()
        return True
    except Exception as e:
        st.error(f"Database error in delete_user_progress: {type(e).__name__}: {e}")
        return False
