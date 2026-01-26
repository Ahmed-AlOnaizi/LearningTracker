import streamlit as st
from utils.auth import supabase, USE_SUPABASE

def get_user_progress(username):
    if not USE_SUPABASE:
        st.error("Supabase not initialized")
        return []
    try:
        response = supabase.table("user_progress").select("*").eq("username", username).execute()
        # Normalize column names to match app expectations
        normalized_data = []
        for row in response.data:
            normalized_data.append({
                'username': row.get('username'),
                'Course': row.get('course', row.get('Course')),
                'Progress %': row.get('progress_percent', row.get('Progress %', 0)),
                'Status': row.get('status', row.get('Status', 'In Progress')),
                'Notes': row.get('notes', row.get('Notes', '')),
                'Last Updated': row.get('last_updated', row.get('Last Updated', ''))
            })
        return normalized_data
    except Exception as e:
        st.error(f"Database error in get_user_progress: {type(e).__name__}: {e}")
        return []

def get_all_progress():
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
                'Course': row.get('course', row.get('Course')),
                'Progress %': row.get('progress_percent', row.get('Progress %', 0)),
                'Status': row.get('status', row.get('Status', 'In Progress')),
                'Notes': row.get('notes', row.get('Notes', '')),
                'Last Updated': row.get('last_updated', row.get('Last Updated', ''))
            })
        return normalized_data
    except Exception as e:
        st.error(f"Database error in get_all_progress: {type(e).__name__}: {e}")
        return []

def upsert_user_progress(progress_dict):
    if not USE_SUPABASE:
        st.error("Supabase not initialized")
        return False
    try:
        # Map to correct Supabase column names (lowercase with underscores)
        supa_dict = {
            "username": progress_dict.get("username"),
            "course": progress_dict.get("Course"),  # Map to lowercase 'course'
            "progress_percent": int(progress_dict.get("Progress %", 0)),  # Map to 'progress_percent'
            "status": progress_dict.get("Status", "In Progress").lower(),  # Map to lowercase 'status'
            "notes": progress_dict.get("Notes", ""),  # Map to lowercase 'notes'
            "last_updated": progress_dict.get("Last Updated", "")  # Map to lowercase 'last_updated'
        }
        # Upsert with correct column names for the unique constraint
        response = supabase.table("user_progress").upsert(supa_dict, on_conflict=["username", "course"]).execute()
        return response.status_code == 201 or response.status_code == 200
    except Exception as e:
        st.error(f"Database error in upsert_user_progress: {type(e).__name__}: {e}")
        return False

def delete_user_progress(username, course):
    if not USE_SUPABASE:
        st.error("Supabase not initialized")
        return False
    try:
        response = supabase.table("user_progress").delete().eq("username", username).eq("course", course).execute()
        return response.status_code == 200
    except Exception as e:
        st.error(f"Database error in delete_user_progress: {type(e).__name__}: {e}")
        return False
