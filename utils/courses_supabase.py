import streamlit as st
from supabase import create_client, Client
import os
import pandas as pd
from datetime import datetime

# This module provides Supabase CRUD for courses, used alongside CSV
SUPABASE_URL = st.secrets.get("SUPABASE_URL", "")
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", "")

if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        USE_SUPABASE = True
    except:
        USE_SUPABASE = False
        supabase = None
else:
    USE_SUPABASE = False
    supabase = None

def get_all_courses():
    if not USE_SUPABASE:
        return []
    try:
        response = supabase.table("courses").select("*").execute()
        return response.data
    except Exception as e:
        st.error(f"Failed to fetch courses: {e}")
        return []

def add_course(course_dict):
    if not USE_SUPABASE:
        return False, "Supabase not configured"
    try:
        supabase.table("courses").insert(course_dict).execute()
        return True, "Course added to Supabase"
    except Exception as e:
        return False, f"Failed to add course: {e}"

def update_course(course_id, update_dict):
    if not USE_SUPABASE:
        return False, "Supabase not configured"
    try:
        supabase.table("courses").update(update_dict).eq("id", course_id).execute()
        return True, "Course updated in Supabase"
    except Exception as e:
        return False, f"Failed to update course: {e}"

def delete_course(course_id):
    if not USE_SUPABASE:
        return False, "Supabase not configured"
    try:
        supabase.table("courses").delete().eq("id", course_id).execute()
        return True, "Course deleted from Supabase"
    except Exception as e:
        return False, f"Failed to delete course: {e}"
