import streamlit as st
from utils.auth import supabase, USE_SUPABASE

def get_user_progress(username):
    if not USE_SUPABASE:
        st.error("Supabase not initialized")
        return []
    try:
        response = supabase.table("user_progress").select("*").eq("username", username).execute()
        return response.data
    except Exception as e:
        st.error(f"Database error in get_user_progress: {type(e).__name__}: {e}")
        return []

def get_all_progress():
    if not USE_SUPABASE:
        st.error("Supabase not initialized")
        return []
    try:
        response = supabase.table("user_progress").select("*").execute()
        return response.data
    except Exception as e:
        st.error(f"Database error in get_all_progress: {type(e).__name__}: {e}")
        return []

def upsert_user_progress(progress_dict):
    if not USE_SUPABASE:
        st.error("Supabase not initialized")
        return False
    try:
        # Normalize keys to match Supabase table columns
        supa_dict = {
            "username": progress_dict.get("username"),
            "Course": progress_dict.get("Course"),
            "Progress %": int(progress_dict.get("Progress %", 0)),
            "Status": progress_dict.get("Status", "In Progress"),
            "Notes": progress_dict.get("Notes", ""),
            "Last Updated": progress_dict.get("Last Updated", "")
        }
        response = supabase.table("user_progress").upsert(supa_dict, on_conflict=["username", "Course"]).execute()
        return response.status_code == 201 or response.status_code == 200
    except Exception as e:
        st.error(f"Database error in upsert_user_progress: {type(e).__name__}: {e}")
        return False

def delete_user_progress(username, course):
    if not USE_SUPABASE:
        st.error("Supabase not initialized")
        return False
    try:
        response = supabase.table("user_progress").delete().eq("username", username).eq("Course", course).execute()
        return response.status_code == 200
    except Exception as e:
        st.error(f"Database error in delete_user_progress: {type(e).__name__}: {e}")
        return False
