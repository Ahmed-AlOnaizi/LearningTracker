# Streamlit Learning Progress Tracker - Setup Guide

## Project Overview
A Streamlit web application for team course progress tracking with dashboard, course management, and progress reporting features.

## Project Setup Checklist

- [x] Verify copilot-instructions.md exists in .github directory
- [x] Project type: Python + Streamlit
- [x] Project structure created with required directories
- [ ] Configure Python environment
- [ ] Install dependencies
- [ ] Run and test application
- [ ] Verify data persistence
- [ ] Team sharing setup (optional)

## Key Files

- `app.py` - Main Streamlit application with all pages and functionality
- `requirements.txt` - Python package dependencies
- `data/progress.csv` - Automatic data storage
- `README.md` - Complete documentation

## Next Steps

1. **Configure Python Environment**: Set up a virtual environment
2. **Install Dependencies**: Run `pip install -r requirements.txt`
3. **Run the App**: Execute `streamlit run app.py`
4. **Access the App**: Open http://localhost:8501 in your browser
5. **Share with Team**: Configure for network sharing if needed

## Features Included

- Dashboard with metrics and course list
- Add new courses with details
- Track progress per course
- View reports and statistics
- Automatic CSV-based data persistence

## Configuration

- App runs on localhost:8501 by default
- Data stored in data/progress.csv
- Responsive design for desktop and tablet
- Multi-page navigation via sidebar

## Quick Start Commands

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

## Notes for Team Sharing

- For local network sharing: `streamlit run app.py --server.address 0.0.0.0`
- For cloud deployment: Use Streamlit Community Cloud or Heroku
- Current implementation uses local CSV; consider database for multiple users
