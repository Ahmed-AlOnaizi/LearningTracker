import hashlib
import pandas as pd
import os

USERS_FILE = "data/users.csv"

def hash_password(password):
    """Simple password hashing"""
    return hashlib.sha256(password.encode()).hexdigest()

def user_exists(username):
    """Check if user already exists"""
    if not os.path.exists(USERS_FILE):
        return False
    df = pd.read_csv(USERS_FILE)
    return username in df['username'].values

def register_user(username, password, is_admin=False):
    """Register a new user. First user is automatically admin."""
    if user_exists(username):
        return False, "Username already exists"
    
    # Check if this is the first user - if so, make them admin
    if not os.path.exists(USERS_FILE) or os.path.getsize(USERS_FILE) <= 0:
        is_admin = True
    
    hashed_pw = hash_password(password)
    new_user = pd.DataFrame({
        'username': [username],
        'password': [hashed_pw],
        'is_admin': [is_admin]
    })
    
    if os.path.exists(USERS_FILE) and os.path.getsize(USERS_FILE) > 0:
        df = pd.read_csv(USERS_FILE)
        df = pd.concat([df, new_user], ignore_index=True)
    else:
        df = new_user
    
    os.makedirs("data", exist_ok=True)
    df.to_csv(USERS_FILE, index=False)
    return True, "User registered successfully"

def verify_login(username, password):
    """Verify username and password"""
    if not os.path.exists(USERS_FILE):
        return False
    
    df = pd.read_csv(USERS_FILE)
    user = df[df['username'] == username]
    
    if user.empty:
        return False
    
    hashed_pw = hash_password(password)
    return user['password'].values[0] == hashed_pw

def is_admin(username):
    """Check if user is admin"""
    if not os.path.exists(USERS_FILE):
        return False
    
    df = pd.read_csv(USERS_FILE)
    user = df[df['username'] == username]
    
    if user.empty:
        return False
    
    return bool(user['is_admin'].values[0])

def make_admin(username):
    """Make a user an admin"""
    if not os.path.exists(USERS_FILE):
        return False
    
    df = pd.read_csv(USERS_FILE)
    df.loc[df['username'] == username, 'is_admin'] = True
    df.to_csv(USERS_FILE, index=False)
    return True
