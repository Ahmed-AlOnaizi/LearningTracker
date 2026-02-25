
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import csv
import os
import json
try:
    import extra_streamlit_components as stx
except Exception:
    stx = None
from utils.auth import (
    register_user,
    verify_login,
    user_exists,
    is_admin,
    make_admin,
    create_remember_session,
    validate_remember_session,
    revoke_remember_session
)
from utils.courses_supabase import get_all_courses, add_course, update_course, delete_course
from utils.progress_supabase import get_user_progress, get_all_progress, upsert_user_progress, delete_user_progress

# File paths (MUST be defined before session state)
DATA_FILE = "data/progress.csv"
USER_PROGRESS_FILE = "data/user_progress.csv"
USERS_FILE = "data/users.csv"
REMEMBER_COOKIE_NAME = "learning_tracker_remember_token"
REMEMBER_DAYS = int(st.secrets.get("REMEMBER_DAYS", 30))
REMEMBER_DEBUG = str(st.secrets.get("REMEMBER_DEBUG", "false")).lower() in {"1", "true", "yes", "on"}


def get_cookie_manager():
    """Initialize cookie manager using the component's recommended pattern."""
    if stx is None:
        return None

    if hasattr(st, "fragment"):
        @st.fragment
        def _cookie_manager_fragment():
            return stx.CookieManager()
        return _cookie_manager_fragment()

    return stx.CookieManager()


def normalize_cookie_token(token):
    """Normalize token value read from browser cookies."""
    if token is None:
        return None
    token = str(token).strip()
    if len(token) >= 2 and token[0] == token[-1] and token[0] in ("'", '"'):
        token = token[1:-1].strip()
    return token or None


def read_remember_token(cookie_manager):
    """Read remember-me token from cookie store."""
    if cookie_manager is None:
        return None
    try:
        cookies = cookie_manager.get_all()
        if isinstance(cookies, dict):
            return normalize_cookie_token(cookies.get(REMEMBER_COOKIE_NAME))
    except Exception:
        pass
    try:
        return normalize_cookie_token(cookie_manager.get(REMEMBER_COOKIE_NAME))
    except Exception:
        return None


def set_remember_token(cookie_manager, token):
    """Persist remember-me token in browser cookie."""
    if cookie_manager is None or not token:
        return False
    try:
        cookie_manager.set(
            REMEMBER_COOKIE_NAME,
            token,
            expires_at=(datetime.utcnow() + timedelta(days=REMEMBER_DAYS))
        )
        return True
    except Exception:
        return False


def clear_remember_token(cookie_manager):
    """Delete remember-me cookie in browser."""
    if cookie_manager is None:
        return
    try:
        cookie_manager.delete(REMEMBER_COOKIE_NAME)
    except Exception:
        pass


def load_courses():
    # Load from Supabase only (primary source)
    from utils.auth import USE_SUPABASE
    courses = []
    if USE_SUPABASE:
        supa_courses = get_all_courses()
        # Normalize keys to match CSV/legacy
        for c in supa_courses:
            courses.append({
                "Course": c.get("course", c.get("Course", "")),
                "Description": c.get("description", c.get("Description", "")),
                "Start Date": c.get("start_date", c.get("Start Date", "")),
                "Target Date": c.get("target_date", c.get("Target Date", "")),
                "Instructor": c.get("instructor", c.get("Instructor", "")),
                "Status": c.get("status", c.get("Status", "")),
                "Progress %": c.get("progress_percent", c.get("Progress %", 0)),
                "Added by": c.get("added_by", c.get("Added by", "")),
                "Last Updated": c.get("last_updated", c.get("Last Updated", "")),
                "id": c.get("id", None)
            })
    return courses

if 'courses' not in st.session_state:
    st.session_state.courses = load_courses()
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'username' not in st.session_state:
    st.session_state.username = None
if 'is_admin' not in st.session_state:
    st.session_state.is_admin = False
if 'edit_course_idx' not in st.session_state:
    st.session_state.edit_course_idx = None
if 'active_session_token' not in st.session_state:
    st.session_state.active_session_token = None
if 'pending_cookie_set_token' not in st.session_state:
    st.session_state.pending_cookie_set_token = None
if 'pending_cookie_clear' not in st.session_state:
    st.session_state.pending_cookie_clear = False

# Helper to load user progress from Supabase or CSV
def load_user_progress(username):
    from utils.auth import USE_SUPABASE
    if USE_SUPABASE:
        progress_data = get_user_progress(username)
        # Normalize keys
        user_progress_data = {}
        for row in progress_data:
            user_progress_data[row['Course']] = {
                'progress': row.get('Progress %', row.get('progress_percent', 0)),
                'status': row.get('Status', row.get('status', 'In Progress')),
                'notes': row.get('Notes', row.get('notes', ''))
            }
        return user_progress_data
    else:
        user_progress_data = {}
        if os.path.exists(USER_PROGRESS_FILE):
            progress_df = pd.read_csv(USER_PROGRESS_FILE)
            user_data = progress_df[progress_df['username'] == username]
            for _, row in user_data.iterrows():
                user_progress_data[row['Course']] = {
                    'progress': row['Progress %'],
                    'status': row['Status'],
                    'notes': row.get('Notes', '')
                }
        return user_progress_data

# Helper to sync user progress to both CSV and Supabase
def save_user_progress_to_backends(progress_dict):
    from utils.auth import USE_SUPABASE
    # Save to Supabase
    if USE_SUPABASE:
        upsert_user_progress(progress_dict)
    # Save to CSV as backup
    if os.path.exists(USER_PROGRESS_FILE):
        progress_df = pd.read_csv(USER_PROGRESS_FILE)
    else:
        progress_df = pd.DataFrame(columns=['username', 'Course', 'Progress %', 'Status', 'Notes', 'Last Updated'])
    mask = (progress_df['username'] == progress_dict['username']) & (progress_df['Course'] == progress_dict['Course'])
    if not progress_df[mask].empty:
        progress_df.loc[mask, 'Progress %'] = progress_dict['Progress %']
        progress_df.loc[mask, 'Status'] = progress_dict['Status']
        progress_df.loc[mask, 'Notes'] = progress_dict['Notes']
        progress_df.loc[mask, 'Last Updated'] = progress_dict['Last Updated']
    else:
        new_entry = pd.DataFrame({
            'username': [progress_dict['username']],
            'Course': [progress_dict['Course']],
            'Progress %': [progress_dict['Progress %']],
            'Status': [progress_dict['Status']],
            'Notes': [progress_dict['Notes']],
            'Last Updated': [progress_dict['Last Updated']]
        })
        progress_df = pd.concat([progress_df, new_entry], ignore_index=True)
    os.makedirs("data", exist_ok=True)
    progress_df.to_csv(USER_PROGRESS_FILE, index=False)
    

# Helper to sync to both CSV and Supabase
def save_course_to_backends(course, supabase_id=None):
    from utils.auth import USE_SUPABASE
    # Save to CSV
    df = pd.DataFrame(st.session_state.courses)
    os.makedirs("data", exist_ok=True)
    df.to_csv(DATA_FILE, index=False)
    # Save to Supabase
    if USE_SUPABASE:
        # Prepare dict for Supabase
        supa_dict = {
            "course": course["Course"],
            "description": course["Description"],
            "start_date": course["Start Date"],
            "target_date": course["Target Date"],
            "instructor": course["Instructor"],
            "status": course["Status"],
            "progress_percent": int(course["Progress %"]),
            "added_by": course["Added by"],
            "last_updated": course["Last Updated"]
        }
        if supabase_id:
            update_course(supabase_id, supa_dict)
        else:
            add_course(supa_dict)

def delete_course_from_backends(idx):
    from utils.auth import USE_SUPABASE
    course = st.session_state.courses[idx]
    supabase_id = course.get("id")
    # Remove from session
    st.session_state.courses.pop(idx)
    # Save to CSV
    df = pd.DataFrame(st.session_state.courses)
    df.to_csv(DATA_FILE, index=False)
    # Remove from Supabase
    if USE_SUPABASE and supabase_id:
        delete_course(supabase_id)


# Cookie manager is optional; app still works without it.
cookie_manager = get_cookie_manager()

# Apply pending cookie operations at the start of a run.
# Important: avoid calling st.rerun in the same run as set/delete.
if cookie_manager is not None:
    if st.session_state.pending_cookie_clear:
        clear_remember_token(cookie_manager)
        st.session_state.pending_cookie_clear = False
    if st.session_state.pending_cookie_set_token:
        if set_remember_token(cookie_manager, st.session_state.pending_cookie_set_token):
            st.session_state.pending_cookie_set_token = None

# Attempt silent auto-login from remember-me token.
if not st.session_state.logged_in and cookie_manager is not None:
    remembered_token = read_remember_token(cookie_manager)
    if remembered_token:
        remembered_user = validate_remember_session(remembered_token)
        if remembered_user:
            st.session_state.logged_in = True
            st.session_state.username = remembered_user
            st.session_state.is_admin = is_admin(remembered_user)
            st.session_state.active_session_token = remembered_token
            st.rerun()
        else:
            if REMEMBER_DEBUG:
                st.caption("Remember debug: cookie token found but session validation failed.")
            clear_remember_token(cookie_manager)
    elif REMEMBER_DEBUG:
        st.caption("Remember debug: no remember cookie found in browser.")

# LOGIN SYSTEM
if not st.session_state.logged_in:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.title("📚 Learning Tracker")
        
        # Check if Supabase is configured
        from utils.auth import USE_SUPABASE, get_all_users
        
        if not USE_SUPABASE:
            st.error("❌ Database not configured")
            st.info("Admin needs to set up Supabase credentials. See SUPABASE_SETUP.md for instructions.")
        else:
            # Check if this is first time setup by checking if any users exist
            existing_users = get_all_users()
            first_time_setup = len(existing_users) == 0

            if first_time_setup:
                st.info("🔐 First time setup - Create your admin account")
                with st.form("setup_admin_form"):
                    setup_user = st.text_input("Choose Admin Username")
                    setup_pass = st.text_input("Choose Admin Password", type="password")
                    setup_pass_confirm = st.text_input("Confirm Password", type="password")

                    if st.form_submit_button("Create Admin Account"):
                        if not setup_user or not setup_pass:
                            st.error("Username and password required")
                        elif setup_pass != setup_pass_confirm:
                            st.error("Passwords don't match")
                        else:
                            success, msg = register_user(setup_user, setup_pass, is_admin=True)
                            if success:
                                st.success("✅ Admin account created! Logging in...")
                                st.session_state.logged_in = True
                                st.session_state.username = setup_user
                                st.session_state.is_admin = True
                                st.rerun()
                            else:
                                st.error(f"❌ {msg}")
            if not first_time_setup:
                auth_tab1, auth_tab2 = st.tabs(["Login", "Register"])

                with auth_tab1:
                    st.subheader("Login")
                    login_user = st.text_input("Username", key="login_user")
                    login_pass = st.text_input("Password", type="password", key="login_pass")
                    remember_me = st.checkbox(
                        "Remember this device",
                        key="remember_me",
                        disabled=(cookie_manager is None)
                    )
                    if cookie_manager is None:
                        st.caption("Remember-me is unavailable until cookie support is installed.")
                    if st.button("Login", key="login_btn"):
                        if verify_login(login_user, login_pass):
                            st.session_state.logged_in = True
                            st.session_state.username = login_user
                            st.session_state.is_admin = is_admin(login_user)

                            # Optional persistent login token.
                            if remember_me and cookie_manager is not None:
                                session_token, _ = create_remember_session(login_user, days_valid=REMEMBER_DAYS)
                                if session_token:
                                    st.session_state.active_session_token = session_token
                                    st.session_state.pending_cookie_set_token = session_token
                                    st.session_state.pending_cookie_clear = False
                                else:
                                    # If the auth_sessions table is missing, keep normal login behavior.
                                    st.session_state.active_session_token = None
                            else:
                                existing_token = read_remember_token(cookie_manager) if cookie_manager is not None else None
                                if existing_token:
                                    revoke_remember_session(existing_token)
                                    st.session_state.pending_cookie_clear = True
                                st.session_state.active_session_token = None
                                st.session_state.pending_cookie_set_token = None

                            st.rerun()
                        else:
                            st.error("Invalid username or password")

                with auth_tab2:
                    st.subheader("Create Account")
                    reg_user = st.text_input("Choose Username", key="reg_user")
                    reg_pass = st.text_input("Choose Password", type="password", key="reg_pass")
                    reg_pass_confirm = st.text_input("Confirm Password", type="password", key="reg_pass_confirm")
                    if st.button("Register", key="reg_btn"):
                        if not reg_user or not reg_pass:
                            st.error("Username and password required")
                        elif reg_pass != reg_pass_confirm:
                            st.error("Passwords don't match")
                        elif user_exists(reg_user):
                            st.error("Username already taken")
                        else:
                            success, msg = register_user(reg_user, reg_pass)
                            if success:
                                st.success(msg)
                            else:
                                st.error(msg)
else:
    # LOGGED IN - MAIN APP
    # Sidebar
    st.sidebar.title("📚 Learning Progress Tracker")
    col_user, col_role = st.sidebar.columns(2)
    with col_user:
        st.write(f"👤 {st.session_state.username}")
    with col_role:
        if st.session_state.is_admin:
            st.write("🔐 **Admin**")
    
    # Build navigation based on role
    nav_options = ["Dashboard", "Track Progress", "View Reports"]
    if st.session_state.is_admin:
        nav_options.insert(1, "Add Course")
        nav_options.append("Admin Panel")
        nav_options.append("Audit Log")
    
    page = st.sidebar.radio("Navigation", nav_options)
    
    if st.sidebar.button("Logout"):
        active_token = st.session_state.get("active_session_token")
        cookie_token = read_remember_token(cookie_manager) if cookie_manager is not None else None

        if active_token:
            revoke_remember_session(active_token)
        if cookie_token:
            revoke_remember_session(cookie_token)
            st.session_state.pending_cookie_clear = True
        st.session_state.pending_cookie_set_token = None

        st.session_state.logged_in = False
        st.session_state.username = None
        st.session_state.is_admin = False
        st.session_state.active_session_token = None
        st.rerun()

    # Main content
    if page == "Audit Log":
        if not st.session_state.is_admin:
            st.error("❌ Access denied!")
        else:
            st.title("📝 Audit Log: User Progress Updates")
            log_path = os.path.join('data', 'audit_log.csv')
            if os.path.exists(log_path):
                log_df = pd.read_csv(log_path)
                log_df = log_df.sort_values('timestamp', ascending=False)
                st.dataframe(log_df, use_container_width=True)
            else:
                st.info('No audit log entries yet.')
    elif page == "Dashboard":
        st.title("📊 Dashboard")
        st.write(f"Welcome back, {st.session_state.username}!")
        
        if st.session_state.courses:
            # Load user progress from Supabase or CSV
            user_progress_data = load_user_progress(st.session_state.username)
            
            # Calculate team stats from Supabase or CSV
            from utils.auth import USE_SUPABASE
            if USE_SUPABASE:
                all_progress = get_all_progress()
                all_progress_df = pd.DataFrame(all_progress)
            elif os.path.exists(USER_PROGRESS_FILE):
                all_progress_df = pd.read_csv(USER_PROGRESS_FILE)
            else:
                all_progress_df = pd.DataFrame()
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Courses", len(st.session_state.courses))
            with col2:
                if not all_progress_df.empty:
                    team_completed = len(all_progress_df[all_progress_df['Status'] == 'Completed'])
                    st.metric("Team Completed", team_completed)
                else:
                    st.metric("Team Completed", 0)
            with col3:
                if not all_progress_df.empty:
                    avg_progress = all_progress_df['Progress %'].mean()
                    st.metric("Avg Team Progress", f"{avg_progress:.1f}%")
                else:
                    st.metric("Avg Team Progress", "0%")
            
            st.subheader("Your Courses")
            
            # Display courses as cards
            for idx, course in enumerate(st.session_state.courses):
                st.markdown("---")
                col1, col2, col3, col4 = st.columns([3, 0.5, 0.5, 0.5])
                
                with col1:
                    st.markdown(f"### {course['Course']}")
                    st.markdown(f"**Deadline:** {course['Target Date']}")
                    st.markdown(f"*{course['Description']}*")
                    
                    # Show user's progress for this course
                    if course['Course'] in user_progress_data:
                        user_prog = user_progress_data[course['Course']]
                        progress_val = int(user_prog['progress'])
                        status = user_prog['status']
                        st.progress(progress_val / 100, text=f"{progress_val}% - {status}")
                    else:
                        st.progress(0, text="Not started")
                
                with col2:
                    st.markdown(f"**By:** {course['Added by']}")
                
                with col3:
                    if st.session_state.is_admin:
                        if st.button("✏️ Edit", key=f"edit_{idx}"):
                            st.session_state.edit_course_idx = idx
                with col4:
                    if st.session_state.is_admin:
                        if st.button("🗑️ Delete", key=f"delete_{idx}"):
                            delete_course_from_backends(idx)
                            st.success("Course deleted!")
                            st.rerun()
            
            # Edit course modal
            if 'edit_course_idx' in st.session_state and st.session_state.edit_course_idx is not None:
                edit_idx = st.session_state.edit_course_idx
                edit_course = st.session_state.courses[edit_idx]
                
                st.markdown("---")
                st.subheader("✏️ Edit Course")
                
                with st.form("edit_course_form"):
                    new_name = st.text_input("Course Name", value=edit_course['Course'])
                    new_desc = st.text_area("Description", value=edit_course['Description'], height=100)
                    new_target = st.date_input("Target Completion Date", value=pd.to_datetime(edit_course['Target Date']).date())
                    new_instructor = st.text_input("Instructor/Platform", value=edit_course['Instructor'])
                    
                    col_save, col_cancel = st.columns(2)
                    with col_save:
                        if st.form_submit_button("Save Changes"):
                            st.session_state.courses[edit_idx]['Course'] = new_name
                            st.session_state.courses[edit_idx]['Description'] = new_desc
                            st.session_state.courses[edit_idx]['Target Date'] = str(new_target)
                            st.session_state.courses[edit_idx]['Instructor'] = new_instructor
                            # Save to both backends
                            save_course_to_backends(st.session_state.courses[edit_idx], st.session_state.courses[edit_idx].get("id"))
                            st.session_state.edit_course_idx = None
                            st.success("✅ Course updated!")
                            st.rerun()
                    
                    with col_cancel:
                        if st.form_submit_button("Cancel"):
                            st.session_state.edit_course_idx = None
                            st.rerun()
        else:
            st.info("No courses available yet.")

    elif page == "Add Course":
        if not st.session_state.is_admin:
            st.error("❌ Only admins can add courses!")
        else:
            st.title("➕ Add Course")
            with st.form("add_course_form"):
                course_name = st.text_input("Course Name")
                course_description = st.text_area("Description")
                start_date = st.date_input("Start Date")
                target_completion = st.date_input("Target Completion Date")
                instructor = st.text_input("Instructor/Platform")
                
                if st.form_submit_button("Add Course"):
                    if course_name:
                        new_course = {
                            "Course": course_name,
                            "Description": course_description,
                            "Start Date": str(start_date),
                            "Target Date": str(target_completion),
                            "Instructor": instructor,
                            "Status": "In Progress",
                            "Progress %": 0,
                            "Added by": st.session_state.username,
                            "Last Updated": str(datetime.now().date())
                        }
                        st.session_state.courses.append(new_course)
                        # Save to both backends
                        save_course_to_backends(new_course)
                        st.success(f"✅ Course '{course_name}' added successfully!")
                    else:
                        st.error("Please enter a course name")

    elif page == "Track Progress":
        st.title("📈 Track Your Progress")
        if st.session_state.courses:
            course_names = [c["Course"] for c in st.session_state.courses]
            selected_course = st.selectbox("Select Course", course_names, key="track_progress_select_course")
            
            # Load user's progress for this course from Supabase or CSV
            user_progress_data = load_user_progress(st.session_state.username)
            user_progress = user_progress_data.get(selected_course, None)
            default_progress = int(user_progress['progress']) if user_progress else 0
            default_status = user_progress['status'] if user_progress else "In Progress"
            default_notes = user_progress['notes'] if user_progress else ""
            
            col1, col2 = st.columns(2)
            with col1:
                progress = st.slider("Your Progress (%)", 0, 100, default_progress, key=f"slider_{selected_course}")
            with col2:
                status = st.selectbox("Status", ["In Progress", "Completed", "On Hold"], 
                                     index=["In Progress", "Completed", "On Hold"].index(default_status), key=f"status_{selected_course}")
            
            notes = st.text_area("Your Notes", value=default_notes, height=100, key=f"notes_{selected_course}")
            
            if st.button("Update My Progress", key=f"update_btn_{selected_course}"):
                progress_dict = {
                    'username': st.session_state.username,
                    'Course': selected_course,
                    'Progress %': progress,
                    'Status': status,
                    'Notes': notes,
                    'Last Updated': str(datetime.now().date())
                }
                save_user_progress_to_backends(progress_dict)
                st.success("✅ Your progress updated!")
                # --- Audit log ---
                log_entry = {
                    'timestamp': datetime.now().isoformat(),
                    'username': st.session_state.username,
                    'course': selected_course,
                    'progress': progress,
                    'status': status,
                    'note': notes
                }
                log_path = os.path.join('data', 'audit_log.csv')
                file_exists = os.path.isfile(log_path)
                with open(log_path, 'a', newline='', encoding='utf-8') as logfile:
                    writer = csv.DictWriter(logfile, fieldnames=log_entry.keys())
                    if not file_exists:
                        writer.writeheader()
                    writer.writerow(log_entry)
        else:
            st.info("No courses available yet.")

    elif page == "View Reports":
        st.title("📊 View Reports")
        if st.session_state.courses:
            st.subheader("Team Progress by Course")
            # Load user progress data
            from utils.auth import USE_SUPABASE
            if USE_SUPABASE:
                all_progress = get_all_progress()
                progress_df = pd.DataFrame(all_progress)
            elif os.path.exists(USER_PROGRESS_FILE):
                progress_df = pd.read_csv(USER_PROGRESS_FILE)
            else:
                progress_df = pd.DataFrame()
            # Create summary by course
            course_summary = []
            for course in st.session_state.courses:
                course_name = course['Course']
                course_data = progress_df[progress_df['Course'] == course_name] if not progress_df.empty else pd.DataFrame()
                if not course_data.empty:
                    avg_progress = course_data['Progress %'].astype(float).mean()
                    completed_count = len(course_data[course_data['Status'] == 'Completed'])
                    total_users = len(course_data)
                else:
                    avg_progress = 0
                    completed_count = 0
                    total_users = 0
                course_summary.append({
                    'Course': course_name,
                    'Team Avg Progress': f"{avg_progress:.1f}%",
                    'Completed': f"{completed_count}/{total_users}",
                    'Total Users': total_users
                })
            summary_df = pd.DataFrame(course_summary)
            st.dataframe(summary_df, use_container_width=True)
            st.subheader("Individual Progress")
            selected_course = st.selectbox("View progress for:", [c['Course'] for c in st.session_state.courses], key="view_reports_select_course")
            course_progress = progress_df[progress_df['Course'] == selected_course][['username', 'Progress %', 'Status', 'Last Updated']] if not progress_df.empty else pd.DataFrame()
            if not course_progress.empty:
                st.dataframe(course_progress, use_container_width=True)
            else:
                st.info("No progress tracked yet for this course.")
        else:
            st.info("No courses available yet.")

    elif page == "Admin Panel":
        if not st.session_state.is_admin:
            st.error("❌ Access denied!")
        else:
            st.title("🔐 Admin Panel")
            
            # Tab for different admin features
            admin_tab1, admin_tab2 = st.tabs(["Users", "Courses"])
            
            with admin_tab1:
                st.subheader("Grant Admin Access")
                from utils.auth import get_all_users
                
                users_list = get_all_users()
                if users_list:
                    non_admin_users = [u['username'] for u in users_list if not u['is_admin']]
                    
                    if non_admin_users:
                        user_to_promote = st.selectbox("Select user to make admin:", non_admin_users)
                        if st.button("Grant Admin Access"):
                            make_admin(user_to_promote)
                            st.success(f"✅ {user_to_promote} is now an admin!")
                            st.rerun()
                    else:
                        st.info("All users are already admins!")
                    
                    st.subheader("All Users")
                    users_df = pd.DataFrame(users_list)
                    st.dataframe(users_df, use_container_width=True)
                else:
                    st.info("No users yet.")
            
            with admin_tab2:
                st.subheader("Course Management")
                
                course_sub_tab1, course_sub_tab2 = st.tabs(["View/Reload", "Edit User Progress"])
                
                with course_sub_tab1:
                    # View all courses in Supabase
                    st.write("**Courses in Supabase Database:**")
                    from utils.auth import USE_SUPABASE
                    if USE_SUPABASE:
                        all_supa_courses = get_all_courses()
                        if all_supa_courses:
                            st.json(all_supa_courses)
                            st.write(f"Total in Supabase: {len(all_supa_courses)}")
                        else:
                            st.info("No courses in Supabase")
                    else:
                        st.error("Supabase not connected")
                    
                    st.divider()
                    
                    # Reload courses from Supabase
                    st.write("**Reload Courses from Supabase:**")
                    if st.button("🔄 Reload All Courses from Supabase"):
                        st.session_state.courses = load_courses()
                        st.success("✅ Courses reloaded from Supabase!")
                        st.rerun()
                
                with course_sub_tab2:
                    st.write("**Edit User Progress in Courses**")
                    from utils.auth import get_all_users
                    
                    users_list = get_all_users()
                    if users_list:
                        usernames = [u['username'] for u in users_list]
                        selected_user = st.selectbox("Select User", usernames, key="progress_user_select")
                        
                        if selected_user and st.session_state.courses:
                            st.write(f"**Editing progress for: {selected_user}**")
                            
                            # Load user progress
                            if os.path.exists(USER_PROGRESS_FILE):
                                progress_df = pd.read_csv(USER_PROGRESS_FILE)
                                user_progress_df = progress_df[progress_df['username'] == selected_user]
                            else:
                                user_progress_df = pd.DataFrame(columns=['username', 'Course', 'Progress %', 'Status', 'Notes', 'Last Updated'])
                            
                            # Display courses for editing
                            for course_idx, course in enumerate(st.session_state.courses):
                                course_name = course['Course']
                                course_prog = user_progress_df[user_progress_df['Course'] == course_name]
                                
                                # Get current values
                                if not course_prog.empty:
                                    current_progress = int(course_prog.iloc[0]['Progress %'])
                                    current_status = course_prog.iloc[0]['Status']
                                    current_notes = course_prog.iloc[0]['Notes']
                                else:
                                    current_progress = 0
                                    current_status = "In Progress"
                                    current_notes = ""
                                
                                with st.expander(f"📚 {course_name}"):
                                    col1, col2 = st.columns(2)
                                    
                                    with col1:
                                        new_progress = st.slider(f"Progress for {course_name}", 0, 100, current_progress, key=f"prog_{selected_user}_{course_idx}")
                                    
                                    with col2:
                                        new_status = st.selectbox(f"Status for {course_name}", ["In Progress", "Completed", "On Hold"], 
                                                                index=["In Progress", "Completed", "On Hold"].index(current_status),
                                                                key=f"status_{selected_user}_{course_idx}")
                                    
                                    new_notes = st.text_area(f"Notes for {course_name}", value=current_notes, height=80, key=f"notes_{selected_user}_{course_idx}")
                                    
                                    if st.button(f"💾 Save Progress for {course_name}", key=f"save_{selected_user}_{course_idx}"):
                                        # Use the same backend sync function as Track Progress
                                        progress_dict = {
                                            'username': selected_user,
                                            'Course': course_name,
                                            'Progress %': new_progress,
                                            'Status': new_status,
                                            'Notes': new_notes,
                                            'Last Updated': str(datetime.now().date())
                                        }
                                        save_user_progress_to_backends(progress_dict)
                                        st.success(f"✅ Progress updated for {course_name}!")
                        elif not st.session_state.courses:
                            st.warning("No courses available yet.")
                    else:
                        st.info("No users found.")
