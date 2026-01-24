import hashlib
import streamlit as st
from supabase import create_client, Client

# Initialize Supabase
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

def hash_password(password):
    """Simple password hashing"""
    return hashlib.sha256(password.encode()).hexdigest()

def user_exists(username):
    """Check if user already exists"""
    if not USE_SUPABASE:
        return False
    
    try:
        response = supabase.table("users").select("*").eq("username", username).execute()
        return len(response.data) > 0
    except Exception as e:
        st.error(f"Database error: {e}")
        return False

def register_user(username, password, is_admin=False):
    """Register a new user. First user is automatically admin."""
    if not USE_SUPABASE:
        return False, "Database not configured"
    
    if user_exists(username):
        return False, "Username already exists"
    
    # Check if this is the first user - if so, make them admin
    try:
        all_users = supabase.table("users").select("*").execute()
        if len(all_users.data) == 0:
            is_admin = True
    except:
        pass
    
    hashed_pw = hash_password(password)
    
    try:
        supabase.table("users").insert({
            "username": username,
            "password": hashed_pw,
            "is_admin": is_admin
        }).execute()
        return True, "User registered successfully"
    except Exception as e:
        return False, f"Registration failed: {str(e)}"

def verify_login(username, password):
    """Verify username and password"""
    if not USE_SUPABASE:
        return False
    
    try:
        response = supabase.table("users").select("*").eq("username", username).execute()
        if len(response.data) == 0:
            return False
        
        user = response.data[0]
        hashed_pw = hash_password(password)
        return user["password"] == hashed_pw
    except Exception as e:
        st.error(f"Login error: {e}")
        return False

def is_admin(username):
    """Check if user is admin"""
    if not USE_SUPABASE:
        return False
    
    try:
        response = supabase.table("users").select("*").eq("username", username).execute()
        if len(response.data) == 0:
            return False
        
        return response.data[0]["is_admin"]
    except Exception as e:
        st.error(f"Database error: {e}")
        return False

def make_admin(username):
    """Make a user an admin"""
    if not USE_SUPABASE:
        return False
    
    try:
        supabase.table("users").update({"is_admin": True}).eq("username", username).execute()
        return True
    except Exception as e:
        st.error(f"Update failed: {e}")
        return False

def get_all_users():
    """Get all users for admin panel"""
    if not USE_SUPABASE:
        return []
    
    try:
        response = supabase.table("users").select("username, is_admin").execute()
        return response.data
    except Exception as e:
        st.error(f"Failed to fetch users: {e}")
        return []
