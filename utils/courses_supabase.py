
import streamlit as st
from utils.auth import supabase, USE_SUPABASE

def get_all_courses():
    if not USE_SUPABASE:
        st.error("Supabase not initialized")
        return []
    try:
        if supabase is None:
            st.error("Supabase client is None")
            return []
        response = supabase.table("courses").select("*").execute()
        st.write(f"DEBUG - Raw Supabase response: {response}")
        return response.data
    except Exception as e:
        st.error(f"Database error in get_all_courses: {type(e).__name__}: {e}")
        import traceback
        st.error(traceback.format_exc())
        return []

def add_course(course_dict):
    if not USE_SUPABASE:
        return False, "Database not configured"
    try:
        if supabase is None:
            return False, "Supabase client is None"
        st.write(f"DEBUG - Adding course to Supabase: {course_dict}")
        result = supabase.table("courses").insert(course_dict).execute()
        st.write(f"DEBUG - Insert result: {result}")
        return True, "Course added successfully"
    except Exception as e:
        st.error(f"Failed to add course: {type(e).__name__}: {e}")
        import traceback
        st.error(traceback.format_exc())
        return False, f"Failed to add course: {e}"

def update_course(course_id, update_dict):
    if not USE_SUPABASE:
        return False, "Database not configured"
    try:
        supabase.table("courses").update(update_dict).eq("id", course_id).execute()
        return True, "Course updated successfully"
    except Exception as e:
        return False, f"Failed to update course: {e}"

def delete_course(course_id):
    if not USE_SUPABASE:
        return False, "Database not configured"
    try:
        supabase.table("courses").delete().eq("id", course_id).execute()
        return True, "Course deleted successfully"
    except Exception as e:
        return False, f"Failed to delete course: {e}"
