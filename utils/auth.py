import hashlib
import secrets
import streamlit as st
from datetime import datetime, timedelta, timezone
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


def _parse_iso_datetime(value):
    """Parse ISO datetime strings from Supabase safely."""
    if not value:
        return None
    try:
        # Supabase often returns trailing Z for UTC.
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except Exception:
        return None

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


def create_remember_session(username, days_valid=30):
    """
    Create a persistent session token for "Remember me".
    Returns (raw_token, expires_at_utc_datetime) or (None, None) on failure.
    """
    if not USE_SUPABASE:
        return None, None

    raw_token = secrets.token_urlsafe(48)
    token_hash = hash_password(raw_token)
    expires_at = datetime.now(timezone.utc) + timedelta(days=days_valid)

    try:
        supabase.table("auth_sessions").insert({
            "username": username,
            "token_hash": token_hash,
            "expires_at": expires_at.isoformat(),
            "revoked": False
        }).execute()
        return raw_token, expires_at
    except Exception:
        # Fail silently so login still works if table isn't created yet.
        return None, None


def validate_remember_session(raw_token):
    """
    Validate remember-me token.
    Returns username when valid, otherwise None.
    """
    if not USE_SUPABASE or not raw_token:
        return None

    token_hash = hash_password(raw_token)
    try:
        response = (
            supabase.table("auth_sessions")
            .select("username, expires_at, revoked")
            .eq("token_hash", token_hash)
            .limit(1)
            .execute()
        )
    except Exception:
        return None

    if not response.data:
        return None

    session_row = response.data[0]
    if session_row.get("revoked", False):
        return None

    expires_at = _parse_iso_datetime(session_row.get("expires_at"))
    if not expires_at:
        return None

    if expires_at <= datetime.now(timezone.utc):
        # Best effort cleanup of expired session.
        revoke_remember_session(raw_token)
        return None

    return session_row.get("username")


def revoke_remember_session(raw_token):
    """Revoke a remember-me token."""
    if not USE_SUPABASE or not raw_token:
        return False

    token_hash = hash_password(raw_token)
    try:
        supabase.table("auth_sessions").update({"revoked": True}).eq("token_hash", token_hash).execute()
        return True
    except Exception:
        return False
