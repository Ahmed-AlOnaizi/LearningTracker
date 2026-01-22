import streamlit as st
import pandas as pd
from datetime import datetime
import os
import json
from utils.auth import register_user, verify_login, user_exists, is_admin, make_admin
from streamlit_cookies_manager import CookieManager

# Page configuration (MUST be first)
st.set_page_config(
    page_title="Learning Progress Tracker",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize cookie manager (after set_page_config)
cookies = CookieManager()

# Initialize session state
if 'courses' not in st.session_state:
    st.session_state.courses = []
if 'logged_in' not in st.session_state:
    # Check if user is saved in cookies
    if cookies.get('username') and cookies.get('session_token'):
        st.session_state.logged_in = True
        st.session_state.username = cookies.get('username')
        st.session_state.is_admin = is_admin(cookies.get('username'))
    else:
        st.session_state.logged_in = False
if 'username' not in st.session_state:
    st.session_state.username = None
if 'is_admin' not in st.session_state:
    st.session_state.is_admin = False
if 'edit_course_idx' not in st.session_state:
    st.session_state.edit_course_idx = None
    
# Load data from CSV if it exists
DATA_FILE = "data/progress.csv"
USER_PROGRESS_FILE = "data/user_progress.csv"

try:
    if os.path.exists(DATA_FILE) and os.path.getsize(DATA_FILE) > 0:
        df = pd.read_csv(DATA_FILE)
        if not df.empty:
            st.session_state.courses = df.to_dict('records')
except pd.errors.EmptyDataError:
    # File is empty, continue with empty courses list
    pass

# LOGIN SYSTEM
if not st.session_state.logged_in:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.title("📚 Learning Tracker")
        auth_tab1, auth_tab2 = st.tabs(["Login", "Register"])
        
        with auth_tab1:
            st.subheader("Login")
            login_user = st.text_input("Username", key="login_user")
            login_pass = st.text_input("Password", type="password", key="login_pass")
            remember_me = st.checkbox("Remember me on this device")
            if st.button("Login", key="login_btn"):
                if verify_login(login_user, login_pass):
                    st.session_state.logged_in = True
                    st.session_state.username = login_user
                    st.session_state.is_admin = is_admin(login_user)
                    
                    # Save to cookies if remember me is checked
                    if remember_me:
                        cookies['username'] = login_user
                        cookies['session_token'] = 'logged_in'
                        cookies.save()
                    
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
    
    page = st.sidebar.radio("Navigation", nav_options)
    
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.username = None
        st.session_state.is_admin = False
        # Clear cookies
        cookies.delete('username')
        cookies.delete('session_token')
        cookies.save()
        st.rerun()

    # Main content
    if page == "Dashboard":
        st.title("📊 Dashboard")
        st.write(f"Welcome back, {st.session_state.username}!")
        
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
                            st.session_state.courses.pop(idx)
                            df = pd.DataFrame(st.session_state.courses)
                            df.to_csv(DATA_FILE, index=False)
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
                            
                            df = pd.DataFrame(st.session_state.courses)
                            df.to_csv(DATA_FILE, index=False)
                            
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
                        
                        # Save to CSV
                        df = pd.DataFrame(st.session_state.courses)
                        os.makedirs("data", exist_ok=True)
                        df.to_csv(DATA_FILE, index=False)
                        
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
            if os.path.exists("data/users.csv"):
                users_df = pd.read_csv("data/users.csv")
                non_admin_users = users_df[users_df['is_admin'] == False]['username'].tolist()
                
                if non_admin_users:
                    user_to_promote = st.selectbox("Select user to make admin:", non_admin_users)
                    if st.button("Grant Admin Access"):
                        make_admin(user_to_promote)
                        st.success(f"✅ {user_to_promote} is now an admin!")
                        st.rerun()
                else:
                    st.info("All users are already admins!")
                
                st.subheader("All Users")
                st.dataframe(users_df[['username', 'is_admin']], use_container_width=True)
            else:
                st.info("No users yet.")
