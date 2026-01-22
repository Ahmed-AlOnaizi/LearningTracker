# Learning Progress Tracker

A simple Streamlit web application for tracking course progress and learning goals as a team.

## Features

- **Dashboard**: Overview of all courses and progress metrics
- **Add Course**: Create new course entries with details
- **Track Progress**: Update progress, status, and notes for each course
- **View Reports**: Visualize progress with charts and summaries
- **Data Persistence**: Automatically saves progress to CSV

## Project Structure

```
LearningApp/
├── app.py                 # Main Streamlit application
├── requirements.txt       # Python dependencies
├── data/                  # Data storage directory
│   └── progress.csv       # Course progress data
├── pages/                 # Additional pages (if needed)
├── utils/                 # Utility functions
└── README.md             # This file
```

## Installation

1. **Install Python** (3.8 or higher)

2. **Clone/Download the project**
   ```
   cd LearningApp
   ```

3. **Create a virtual environment (recommended)**
   ```
   python -m venv venv
   venv\Scripts\activate
   ```

4. **Install dependencies**
   ```
   pip install -r requirements.txt
   ```

## Running the Application

```bash
streamlit run app.py
```

The app will open in your default browser at `http://localhost:8501`

## Usage

1. **Add Courses**: Navigate to "Add Course" and enter course details
2. **Track Progress**: Update progress percentage, status, and add notes
3. **View Dashboard**: See overview of all courses at a glance
4. **Check Reports**: View charts and statistics

## Team Sharing

To share this app with your team:

1. Run the app on a shared server or use Streamlit Community Cloud
2. Share the URL with team members
3. Each team member can view and update progress

### Local Network Sharing

```bash
streamlit run app.py --server.address 0.0.0.0 --server.port 8501
```

Then share your IP address: `http://<your-ip>:8501`

## Data Storage

Progress data is saved automatically to `data/progress.csv`. You can:
- Export the CSV for reports
- Back it up regularly
- Share it with the team

## Customization

- Modify `app.py` to add more fields or features
- Adjust styling in Streamlit configuration
- Add more pages in the `pages/` directory

## Requirements

- Python 3.8+
- Streamlit
- Pandas
- Plotly (for advanced charts)

## Future Enhancements

- User authentication
- Database integration
- Email notifications
- Mobile app
- Team collaboration features

## Support

For issues or questions, refer to [Streamlit Documentation](https://docs.streamlit.io/)
