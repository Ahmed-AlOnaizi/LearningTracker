
import streamlit as st
import pandas as pd
from datetime import datetime
import csv
import os
import json
from utils.auth import register_user, verify_login, user_exists, is_admin, make_admin
from utils.courses_supabase import get_all_courses, add_course, update_course, delete_course

# File paths (MUST be defined before session state)
DATA_FILE = "data/progress.csv"
USER_PROGRESS_FILE = "data/user_progress.csv"
USERS_FILE = "data/users.csv"

def load_courses():
    # Try Supabase first, then fallback to CSV
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
    # Always also load from CSV for backup/merge
    if os.path.exists(DATA_FILE):
        try:
            df = pd.read_csv(DATA_FILE)
            for _, row in df.iterrows():
                course = row.to_dict()
                if course not in courses:
                    courses.append(course)
        except Exception:
            pass
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
    

# Helper to sync to both CSV and Supabase
def save_course_to_backends(course, supabase_id=None):
    from utils.auth import USE_SUPABASE
    # Save to CSV
    df = pd.DataFrame(st.session_state.courses)
    os.makedirs("data", exist_ok=True)
    df.to_csv(DATA_FILE, index=False)
    st.write(f"DEBUG - Saved to CSV: {course}")
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
        st.write(f"DEBUG - About to save to Supabase: {supa_dict}")
        if supabase_id:
            success, msg = update_course(supabase_id, supa_dict)
            st.write(f"DEBUG - Update result: {success}, {msg}")
        else:
            success, msg = add_course(supa_dict)
            st.write(f"DEBUG - Add result: {success}, {msg}")

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
            else:
                auth_tab1, auth_tab2 = st.tabs(["Login", "Register"])
            
            with auth_tab1:
                st.subheader("Login")
                login_user = st.text_input("Username", key="login_user")
                login_pass = st.text_input("Password", type="password", key="login_pass")
                if st.button("Login", key="login_btn"):
                    if verify_login(login_user, login_pass):
                        st.session_state.logged_in = True
                        st.session_state.username = login_user
                        st.session_state.is_admin = is_admin(login_user)
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
    st.write(f"DEBUG: selected page = {page}")
    
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.username = None
        st.session_state.is_admin = False
        st.rerun()

    # Main content
    if page == "Audit Log":
        st.write(f"DEBUG: selected page = {page}")
        st.write(f"DEBUG: is_admin = {st.session_state.get('is_admin')}")
        if not st.session_state.is_admin:
            st.error("❌ Access denied!")
        else:
            st.title("📝 Audit Log: User Progress Updates")
            log_path = os.path.join('data', 'audit_log.csv')
            if os.path.exists(log_path):
                log_df = pd.read_csv(log_path)
                log_df = log_df.sort_values('timestamp', ascending=False)
                st.write("DEBUG: log_df", log_df)
                st.dataframe(log_df, use_container_width=True)
            else:
                st.info('No audit log entries yet.')
    elif page == "Dashboard":
        st.title("📊 Dashboard")
        st.write(f"Welcome back, {st.session_state.username}!")
        
        # DEBUG: Show what's being loaded
        with st.expander("🔧 DEBUG: Course Loading Info"):
            from utils.auth import USE_SUPABASE
            st.write(f"**Supabase Connected:** {USE_SUPABASE}")
            supa_courses = get_all_courses()
            st.write(f"**Courses from Supabase:** {len(supa_courses)}")
            if supa_courses:
                st.json(supa_courses)
            st.write(f"**Courses in Session State:** {len(st.session_state.courses)}")
            st.json(st.session_state.courses)
        
        if st.session_state.courses:
            # Load user progress
            user_progress_data = {}
            if os.path.exists(USER_PROGRESS_FILE):
                progress_df = pd.read_csv(USER_PROGRESS_FILE)
                user_data = progress_df[progress_df['username'] == st.session_state.username]
                for _, row in user_data.iterrows():
                    user_progress_data[row['Course']] = {
                        'progress': row['Progress %'],
                        'status': row['Status']
                    }
            
            # Calculate team stats
            if os.path.exists(USER_PROGRESS_FILE):
                all_progress = pd.read_csv(USER_PROGRESS_FILE)
            else:
                all_progress = pd.DataFrame()
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Courses", len(st.session_state.courses))
            with col2:
                if not all_progress.empty:
                    team_completed = len(all_progress[all_progress['Status'] == 'Completed'])
                    st.metric("Team Completed", team_completed)
                else:
                    st.metric("Team Completed", 0)
            with col3:
                if not all_progress.empty:
                    avg_progress = all_progress['Progress %'].mean()
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
                    st.markdown(f"*{course['Description'][:100]}...*" if len(course['Description']) > 100 else f"*{course['Description']}*")
                    
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
            selected_course = st.selectbox("Select Course", course_names)
            
            # Find the selected course
            course_idx = next((i for i, c in enumerate(st.session_state.courses) if c["Course"] == selected_course), None)
            
            if course_idx is not None:
                # Load user's progress for this course
                if os.path.exists(USER_PROGRESS_FILE):
                    progress_df = pd.read_csv(USER_PROGRESS_FILE)
                    user_progress = progress_df[(progress_df['username'] == st.session_state.username) & 
                                               (progress_df['Course'] == selected_course)]
                    if not user_progress.empty:
                        user_progress = user_progress.iloc[0].to_dict()
                    else:
                        user_progress = None
                else:
                    user_progress = None
                
                # Get defaults from user progress or course
                default_progress = int(user_progress.get("Progress %", 0)) if user_progress else 0
                default_status = user_progress.get("Status", "In Progress") if user_progress else "In Progress"
                default_notes = user_progress.get("Notes", "") if user_progress else ""
                
                col1, col2 = st.columns(2)
                
                with col1:
                    progress = st.slider("Your Progress (%)", 0, 100, default_progress)
                
                with col2:
                    status = st.selectbox("Status", ["In Progress", "Completed", "On Hold"], 
                                         index=["In Progress", "Completed", "On Hold"].index(default_status))
                
                notes = st.text_area("Your Notes", value=default_notes, height=100)
                
                if st.button("Update My Progress"):
                    # Load existing user progress
                    if os.path.exists(USER_PROGRESS_FILE):
                        progress_df = pd.read_csv(USER_PROGRESS_FILE)
                    else:
                        progress_df = pd.DataFrame(columns=['username', 'Course', 'Progress %', 'Status', 'Notes', 'Last Updated'])
                    
                    # Update or create progress entry
                    if len(progress_df) > 0:
                        mask = (progress_df['username'] == st.session_state.username) & (progress_df['Course'] == selected_course)
                    else:
                        mask = pd.Series([False] * len(progress_df))
                    
                    if not progress_df[mask].empty:
                        progress_df.loc[mask, 'Progress %'] = progress
                        progress_df.loc[mask, 'Status'] = status
                        progress_df.loc[mask, 'Notes'] = notes
                        progress_df.loc[mask, 'Last Updated'] = str(datetime.now().date())
                    else:
                        new_entry = pd.DataFrame({
                            'username': [st.session_state.username],
                            'Course': [selected_course],
                            'Progress %': [progress],
                            'Status': [status],
                            'Notes': [notes],
                            'Last Updated': [str(datetime.now().date())]
                        })
                        progress_df = pd.concat([progress_df, new_entry], ignore_index=True)
                    
                    # Save
                    os.makedirs("data", exist_ok=True)
                    progress_df.to_csv(USER_PROGRESS_FILE, index=False)
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
            elif page == "Audit Log":
                st.write(f"DEBUG: page = {page}")
                st.write(f"DEBUG: is_admin = {st.session_state.get('is_admin')}")
                if not st.session_state.is_admin:
                    st.error("❌ Access denied!")
                else:
                    st.title("📝 Audit Log: User Progress Updates")
                    log_path = os.path.join('data', 'audit_log.csv')
                    if os.path.exists(log_path):
                        log_df = pd.read_csv(log_path)
                        log_df = log_df.sort_values('timestamp', ascending=False)
                        st.write("DEBUG: log_df", log_df)
                        st.dataframe(log_df, use_container_width=True)
                    else:
                        st.info('No audit log entries yet.')
        else:
            st.info("No courses available yet.")

    elif page == "View Reports":
        st.title("📊 View Reports")
        if st.session_state.courses:
            st.subheader("Team Progress by Course")
            
            # Load user progress data
            if os.path.exists(USER_PROGRESS_FILE):
                progress_df = pd.read_csv(USER_PROGRESS_FILE)
                
                # Create summary by course
                course_summary = []
                for course in st.session_state.courses:
                    course_name = course['Course']
                    course_data = progress_df[progress_df['Course'] == course_name]
                    
                    if not course_data.empty:
                        avg_progress = course_data['Progress %'].mean()
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
                selected_course = st.selectbox("View progress for:", [c['Course'] for c in st.session_state.courses])
                
                course_progress = progress_df[progress_df['Course'] == selected_course][['username', 'Progress %', 'Status', 'Last Updated']]
                if not course_progress.empty:
                    st.dataframe(course_progress, use_container_width=True)
                else:
                    st.info("No progress tracked yet for this course.")
            else:
                st.info("No progress tracked yet.")
        else:
            st.info("No courses available yet.")

    elif page == "Admin Panel":
        if not st.session_state.is_admin:
            st.error("❌ Access denied!")
        else:
            st.title("🔐 Admin Panel")
            
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
