# AI Career Agent -- User Manual

**For Senior IT Leaders**

---

## Table of Contents

1. [Welcome and Introduction](#1-welcome-and-introduction)
2. [Getting Started](#2-getting-started)
3. [Dashboard Overview](#3-dashboard-overview)
4. [Managing Your Profile](#4-managing-your-profile)
5. [Job Board](#5-job-board)
6. [Application Tracker](#6-application-tracker)
7. [Career Insights](#7-career-insights)
8. [Interview Preparation](#8-interview-preparation)
9. [Troubleshooting](#9-troubleshooting)
10. [Frequently Asked Questions](#10-frequently-asked-questions)

---

## 1. Welcome and Introduction

### 1.1 What is AI Career Agent

AI Career Agent is an intelligent career management system built specifically for senior IT leaders. It uses artificial intelligence -- specifically Retrieval-Augmented Generation (RAG) and large language models -- to help you navigate your career transition with data-driven precision.

The system analyzes your professional background against real job opportunities, generates tailored application materials, and provides actionable insights about your job search patterns. Think of it as a personal career strategist that works around the clock.

### 1.2 Who is it for

This tool is designed for:

- **Senior IT Directors** looking for C-suite or VP-level opportunities
- **VPs of Engineering** transitioning to new organizations
- **CTOs** exploring their next leadership role
- **IT Program Managers** targeting senior leadership positions
- **Platform Engineering Leaders** seeking director or above roles

If you hold or are targeting a senior technology leadership position, this system was built for you.

### 1.3 Key Benefits

- **Intelligent Job Matching**: AI-powered scoring that evaluates your fit against specific job requirements, weighted across skills, experience, industry relevance, and leadership signals
- **Tailored Application Materials**: Automatically generated resumes and cover letters customized for each opportunity
- **Pattern Recognition**: Identifies what is working and what is not in your job search strategy
- **Interview Preparation**: AI-generated interview questions and STAR-format answers drawn from your actual experience
- **Centralized Tracking**: Manage all your applications, statuses, and feedback in one place
- **Executive Dashboard**: Clear metrics on your job search performance at a glance

---

## 2. Getting Started

### 2.1 System Requirements

Before installation, confirm your system meets these requirements:

| Requirement | Minimum | Recommended |
|---|---|---|
| Operating System | macOS 12+, Windows 10+, or Linux | macOS or Linux |
| Python | 3.11 or higher | 3.11 or 3.12 |
| RAM | 4 GB | 8 GB or more |
| Disk Space | 500 MB | 1 GB (for models and data) |
| Internet | Required for cloud AI | Stable broadband connection |

You will also need:

- A **text editor** (for configuration files)
- **Terminal** or **Command Prompt** access
- An **Nvidia NIM API key** (free tier available at https://build.nvidia.com/)

### 2.2 Installation Steps

Follow these steps in order. Each step builds on the previous one.

**Step 1: Open your terminal**

On macOS, open the **Terminal** application (found in Applications > Utilities). On Windows, open **PowerShell** or **Command Prompt**.

**Step 2: Navigate to the project directory**

```bash
cd "AI_Career_Agent_for_Senior_IT_Leaders"
```

If you received the project as a zip file, extract it first and then navigate to the extracted folder.

**Step 3: Create a virtual environment**

A virtual environment keeps the project's dependencies isolated from your system Python.

```bash
python -m venv venv
```

Activate it:

```bash
# macOS / Linux
source venv/bin/activate

# Windows
venv\Scripts\activate
```

You will know it is active when you see `(venv)` at the start of your terminal prompt.

**Step 4: Install dependencies**

```bash
pip install -r requirements.txt
```

This installs all required libraries. It may take a few minutes on first run.

**Step 5: Configure your API key**

Copy the example configuration file:

```bash
cp .env.example .env
```

Open the `.env` file in any text editor and replace the placeholder with your actual Nvidia NIM API key:

```
NVIDIA_API_KEY=your-actual-api-key-here
```

Leave all other settings at their defaults unless you are using a local LLM (see Section 10 for details).

**Step 6: Start the backend server**

Open a new terminal tab or window and run:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

You should see output indicating the server is running. Leave this terminal open.

**Step 7: Start the frontend**

Open another terminal tab or window, activate the virtual environment again, and run:

```bash
streamlit run frontend/streamlit_app.py
```

Your web browser should automatically open to the application at `http://localhost:8501`.

### 2.3 First-Time Setup

When you first open the application:

1. The **Dashboard** will appear with zero values -- this is normal
2. Your **Profile ID** defaults to 1 (shown in the left sidebar). This is your profile. All data you enter is associated with this ID
3. Start by uploading your resume (see Section 4)

### 2.4 Logging In

The application does not require a login or password. It runs entirely on your local machine. Your data never leaves your computer except for the AI analysis calls to the Nvidia NIM API.

To access the application, open your browser and navigate to:

```
http://localhost:8501
```

---

## 3. Dashboard Overview

The Dashboard is the first screen you see. It provides a high-level summary of your career intelligence.

### 3.1 What Each Metric Means

The Dashboard displays four key metrics across the top:

| Metric | What It Means |
|---|---|
| **Total Applications** | The number of job applications you are currently tracking. This includes all statuses: applied, interviewing, offered, rejected, ghosted, or withdrawn. |
| **Interview Rate** | The percentage of your applications that have progressed to at least one interview stage. A healthy rate for senior roles is typically 20-35%. |
| **Rejection Rate** | The percentage of applications that resulted in a rejection. For senior roles, some rejections are expected -- what matters is the trend over time. |
| **Avg Match Score** | The average AI-calculated match score across all jobs you have analyzed. Scores above 75% indicate strong alignment with the roles you are targeting. |

### 3.2 How to Read the Funnel Chart

The Application Tracker section contains a funnel visualization. The funnel shows your applications moving through stages:

```
Applied (all applications submitted)
    |
    v
Interview (phone screen, technical, or final interview)
    |
    v
Offer (received an offer)
```

The funnel also shows:

- **Applied to Interview Rate**: What percentage of your applications lead to interviews
- **Interview to Offer Rate**: What percentage of interviews convert to offers
- **Overall Success Rate**: Total offers divided by total applications
- **Rejection Rate**: How many applications end in rejection

A narrow funnel (few interviews relative to applications) suggests your targeting or resume may need adjustment. A funnel that widens at the interview stage but narrows at offers may indicate interview performance opportunities.

### 3.3 Interpreting Match Scores

The AI assigns a match score from 0 to 100 for each job you analyze:

| Score Range | Interpretation | Color | Recommendation |
|---|---|---|---|
| 75-100 | **Strong Match** | Green | Apply with confidence. Your profile aligns well with this role. |
| 50-74 | **Moderate Match** | Yellow | Consider applying, but review the gaps section for areas to address in your application. |
| 0-49 | **Weak Match** | Red | Review carefully. Significant gaps exist between your profile and the role requirements. |

The score is calculated using four weighted criteria:

1. **Skills Match (30%)**: Alignment of your technical and soft skills with job requirements
2. **Experience Level (25%)**: Whether your seniority and years of experience match the role
3. **Industry Relevance (20%)**: How relevant your industry background is to the position
4. **Leadership Signals (25%)**: Evidence of strategic thinking, team leadership, and executive presence

---

## 4. Managing Your Profile

Your profile is the foundation of all AI analysis. The more complete your profile, the more accurate the matching and material generation.

### 4.1 Uploading Your Resume (Step by Step)

Your resume is the starting point. The system parses it and uses AI to expand it into a rich career profile.

**Step 1**: Click **Profile** in the left sidebar navigation.

**Step 2**: You will see three tabs at the top: **Resume Upload**, **Detailed Profile**, and **Profile Chunks**. The Resume Upload tab is selected by default.

**Step 3**: Click the **Browse files** button (labeled "Upload your resume (PDF, DOCX, or TXT)").

**Step 4**: Select your resume file from your computer. The system accepts:
- PDF files (.pdf)
- Microsoft Word documents (.docx)
- Plain text files (.txt)

**Step 5**: Once the file is selected, click the **Upload & Process Resume** button.

**Step 6**: Wait for the processing to complete. You will see a spinner with "Processing your resume..." This typically takes 15-30 seconds.

**Step 7**: When complete, you will see a success message and a JSON summary showing:
- Your profile ID
- A professional summary generated by AI
- The number of projects extracted
- The number of skills identified

**Important**: If your resume is in PDF format, ensure it is text-based (not a scanned image). Scanned PDFs will not parse correctly.

### 4.2 Adding Detailed Projects

After uploading your resume, you can add richer project details. These are especially valuable for interview preparation and job matching.

**Step 1**: On the Profile page, click the **Detailed Profile** tab.

**Step 2**: You will see a form with the following fields:

*Required fields (marked with asterisks):*
- **Project Title**: Name of the project or initiative (e.g., "Enterprise Cloud Migration Program")
- **Your Role**: Your specific title and responsibilities (e.g., "Executive Sponsor and Technical Lead")
- **Technologies Used**: Key technologies involved (e.g., "AWS, Kubernetes, Terraform, Jenkins")
- **Project Description**: A narrative overview of the project
- **Business Impact & Results**: Quantifiable outcomes (e.g., "Reduced infrastructure costs by 40% while improving system reliability to 99.99% uptime")

*STAR Method Details (optional but recommended):*
- **Situation**: The context and background. What was happening in the organization?
- **Task**: Your specific responsibility. What were you accountable for?
- **Action**: What you did. Describe the steps you took.
- **Result**: Measurable outcomes. What was the quantifiable impact?

**Step 3**: Fill in all relevant fields. The STAR fields are particularly valuable for interview preparation.

**Step 4**: Click **Save Project**.

**Step 5**: Repeat for each significant project you want to include.

**Tip**: Add 3-5 of your most impactful projects. Focus on projects that demonstrate leadership, strategic decision-making, and measurable business outcomes.

### 4.3 Understanding Career Expansion

When you upload your resume, the system uses AI to "expand" it into a richer career profile. This means:

- Your resume bullet points are expanded into detailed project narratives
- Skills are categorized into logical groups (leadership, technical, methodologies, platforms)
- STAR stories are generated from your described experience
- A professional summary is created

This expansion happens automatically. You do not need to do anything -- it runs as part of the resume upload process.

The expanded profile is what the AI uses when matching you against jobs and generating application materials.

### 4.4 Updating Your Profile

To update your profile after the initial upload:

1. Upload a new resume (this will create a new profile entry)
2. Add additional projects via the Detailed Profile tab
3. The system will automatically re-index your career data for matching

When you update your profile, the AI re-processes your career information and updates the vector database used for matching. This ensures all future analyses reflect your most current background.

---

## 5. Job Board

The Job Board is where you manage job opportunities and generate application materials.

### 5.1 Adding a Job Posting (Manual Input)

**Step 1**: Click **Job Board** in the left sidebar.

**Step 2**: You will see three tabs: **Add Job**, **All Jobs**, and **Match & Generate**. The Add Job tab is selected by default.

**Step 3**: Fill in the Add Job form:

| Field | Required | Description |
|---|---|---|
| Company | Yes | The company name (e.g., "FinServe Global") |
| Position Title | Yes | The job title (e.g., "Senior Director of Platform Engineering") |
| Location | No | Job location (e.g., "New York, NY" or "Remote") |
| Job URL | No | A link to the original posting |
| Full Job Description | Yes | Paste the complete job description text here |
| Salary Range | No | If provided in the listing (e.g., "$180,000 - $220,000") |

**Step 4**: Click **Add Job**.

The system will:
- Parse the job description using AI
- Extract the job title, company, location, seniority level, and required skills
- Store the structured data in the database
- Index the job for matching

**Quick Add Alternative**: Below the form, there is a "Quick Add & Match" text area. Paste a job description there, click the button, and the system will add the job and immediately run a match analysis against your profile.

### 5.2 Understanding Parsed Job Data

When you add a job, the system extracts structured information from the raw text:

| Extracted Field | What It Means |
|---|---|
| **Title** | The normalized job title (e.g., "Senior Director of Platform Engineering") |
| **Company** | The employer name |
| **Location** | Geographic location or "Remote" |
| **Seniority Level** | Detected level (e.g., "Director", "VP", "C-Suite") |
| **Required Skills** | A list of technical and leadership skills the role demands |
| **Requirements** | The full requirements text |

This parsed data is what the AI uses when evaluating your fit for the role.

### 5.3 Running a Job Match

**Step 1**: Click the **Match & Generate** tab on the Job Board page.

**Step 2**: Select a job from the dropdown list. Each entry shows the company, position, and ID number.

**Step 3**: Click **Run Match Analysis**.

**Step 4**: Wait for the analysis. This typically takes 20-45 seconds as the AI retrieves your career data and evaluates it against the job requirements.

### 5.4 Reading Match Results

After the analysis completes, the results appear below the buttons.

**Match Score**: A large number (0-100%) with color coding:
- Green (75+): Strong alignment
- Yellow (50-74): Moderate alignment
- Red (below 50): Weak alignment

**Strengths**: A bulleted list of areas where your profile aligns well with the role. These are drawn from your actual career data -- not fabricated.

**Gaps to Address**: A bulleted list of areas where your profile falls short of the role requirements. Use these to decide whether to apply and what to emphasize in your application.

**Evidence**: Specific references to your career data that support the match assessment. Each entry shows which part of your career profile was relevant and how.

**Explanation**: A paragraph explaining the overall match quality and why the score was given.

**Recommendation**: One of three categories:
- **strong_match**: Apply with confidence
- **moderate_match**: Consider applying; address gaps in your cover letter
- **weak_match**: Review carefully; may not be the best use of your time

### 5.5 Generating Tailored Resume and Cover Letter

**Step 1**: On the Match & Generate tab, select a job from the dropdown.

**Step 2**: Click **Generate Resume & Cover Letter**.

**Step 3**: Wait for generation. This typically takes 30-60 seconds.

**Step 4**: When complete, two expandable sections appear:

**Tailored Resume**: A complete resume customized for this specific job. It:
- Emphasizes experience relevant to this role
- Uses language aligned with the job requirements
- Highlights leadership and strategic impact
- Includes quantifiable achievements

**Cover Letter**: A one-page letter addressed to the hiring manager. It:
- Opens with a connection between your experience and the role
- Highlights 3-4 key qualifications
- References the company and role specifically
- Closes with a confident call to action

**Important**: The generated materials use only information from your uploaded resume and added projects. If the AI does not have enough data about a particular area, it will omit that section rather than fabricate content. Review and personalize the output before submitting.

---

## 6. Application Tracker

The Application Tracker helps you monitor every opportunity from initial submission through final decision.

### 6.1 Tracking a New Application

**Step 1**: Click **Application Tracker** in the left sidebar.

**Step 2**: Click the **Track Application** tab.

**Step 3**: Select a job from the dropdown (you must have jobs in your Job Board first).

**Step 4**: Select the initial status:
- **applied** -- You have submitted your application
- **interview** -- You are in an interview process
- **offer** -- You have received an offer
- **rejected** -- You have been rejected
- **ghosted** -- You have not received a response
- **withdrawn** -- You have withdrawn your application

**Step 5**: Optionally add notes (e.g., "Applied via referral from John Smith").

**Step 6**: Click **Track Application**.

### 6.2 Updating Application Status

As your application progresses, update its status:

**Step 1**: Click the **Update Status** tab on the Application Tracker page.

**Step 2**: Select the application from the dropdown. Each entry shows the application ID, company, position, and current status.

**Step 3**: Select the new status from the dropdown.

**Step 4**: Optionally add feedback notes. These notes are valuable for the AI insight analysis (see Section 7).

**Step 5**: Click **Update Status**.

Available statuses and their meanings:

| Status | Meaning |
|---|---|
| **applied** | Application submitted, awaiting response |
| **interview** | You are in an active interview process |
| **offer** | You have received a formal offer |
| **rejected** | The employer has declined your application |
| **ghosted** | No response received within a reasonable timeframe |
| **withdrawn** | You have decided not to pursue this opportunity |

### 6.3 Understanding the Funnel View

The **Funnel View** tab shows a visual representation of your application pipeline.

**Bar Chart**: Displays the count of applications in each status category.

**Conversion Rates**: Four key metrics are calculated:

| Metric | Calculation | What It Tells You |
|---|---|---|
| **Applied to Interview** | (Interviews / Total Applications) x 100 | How effectively your applications convert to conversations |
| **Interview to Offer** | (Offers / Interviews) x 100 | Your interview performance effectiveness |
| **Overall Success** | (Offers / Total Applications) x 100 | Your total conversion rate |
| **Rejection Rate** | (Rejections / Total Applications) x 100 | What percentage of applications are declined |

**All Applications Table**: A detailed list of every tracked application with its current status, date applied, and any notes.

### 6.4 Adding Feedback Notes

When updating an application status, you can add feedback notes. These notes serve two purposes:

1. **Personal reference**: Remember details about specific interactions
2. **AI analysis**: The Insight Agent uses feedback notes to identify patterns

Examples of useful feedback notes:
- "Interviewer emphasized Kubernetes experience -- I should highlight this more"
- "They were concerned about my lack of fintech experience"
- "Received positive feedback on my cloud migration story"
- "Rejected after final round -- they chose a candidate with more M&A experience"

---

## 7. Career Insights

The Insights page provides AI-powered analysis of your job search performance.

### 7.1 Generating Insights

**Step 1**: Click **Insights** in the left sidebar.

**Step 2**: Click the **Generate Insights** button.

**Step 3**: Wait for the analysis. This typically takes 30-60 seconds as the AI examines your application history, match results, and career profile.

**Step 4**: The insights appear in categorized sections.

### 7.2 Understanding Rejection Patterns

The **Rejection Patterns** section identifies trends in why applications may not be progressing. Examples:

- "Rejections tend to occur at the final interview stage for roles requiring specific industry experience"
- "Applications to companies with fewer than 500 employees have a higher rejection rate"
- "Technical interview rejections correlate with roles requiring hands-on coding"

These patterns help you focus your efforts on roles where you are most competitive.

### 7.3 Reading Improvement Suggestions

The **Improvement Suggestions** section provides actionable recommendations:

- "Consider adding more fintech-specific projects to your profile to improve match scores for financial services roles"
- "Your interview conversion rate improves when you emphasize platform engineering experience -- highlight this earlier in applications"
- "Applications with tailored cover letters have a 2x higher interview rate"

Each suggestion is based on patterns observed in your actual data.

### 7.4 Using Insights to Improve Your Strategy

To make the most of insights:

1. **Review regularly**: Generate insights after every 5-10 new applications
2. **Act on patterns**: If a pattern emerges, adjust your approach
3. **Add feedback**: The more feedback notes you add to applications, the richer the insights
4. **Update your profile**: If insights suggest gaps, add projects or skills that address them
5. **Re-run match analyses**: After updating your profile, re-match against jobs to see improved scores

---

## 8. Interview Preparation

The Interview Prep feature generates customized preparation materials for specific job opportunities.

### 8.1 Generating Interview Prep for a Job

**Step 1**: Click **Interview Prep** in the left sidebar.

**Step 2**: Select a job from the dropdown. You must have jobs in your Job Board.

**Step 3**: Click **Generate Interview Prep**.

**Step 4**: Wait for generation. This typically takes 30-60 seconds.

**Step 5**: The preparation materials appear in several sections.

### 8.2 Understanding STAR Answers

The system generates STAR-format answers for likely interview questions. STAR stands for:

- **Situation**: The context and background of a specific experience
- **Task**: Your specific responsibility or challenge
- **Action**: The concrete steps you took to address the situation
- **Result**: The measurable outcome of your actions

Each answer is drawn from your actual career data -- the projects you added and the experience in your resume. The AI does not invent stories.

**Example STAR Structure**:

```
Question: "Tell me about a time you led a major technology migration."

Situation: [Context from your career data]
Task: [Your specific responsibility]
Action: [Steps you took]
Result: [Quantifiable outcome]
```

### 8.3 Practicing with Likely Questions

The system generates 8-12 likely interview questions tailored to the specific role and seniority level. These questions are based on:

- The job requirements and responsibilities
- Common questions for similar senior IT roles
- Your specific career background

**Practice Tips**:

1. Read each question and mentally rehearse your answer before expanding the STAR response
2. Time yourself -- senior-level answers should be 2-3 minutes each
3. Focus on quantifiable results (percentages, dollar amounts, team sizes)
4. Practice transitioning between stories smoothly
5. Note any questions where you struggle -- these indicate areas to prepare further

**Additional Sections**:

- **Key Talking Points**: Themes to emphasize throughout the interview
- **Company Research Notes**: Background on the company and role context
- **Interview Strategy**: Overall approach recommended for this specific opportunity

---

## 9. Troubleshooting

### 9.1 Common Errors and Solutions

| Error | Likely Cause | Solution |
|---|---|---|
| "Cannot connect to backend" | The FastAPI server is not running | Start the backend: `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000` |
| "API error: 404" | The endpoint URL is incorrect or the resource does not exist | Verify the job or profile ID exists. Check the API docs at `http://localhost:8000/docs` |
| "API error: 422" | Invalid request data | Check that all required fields are provided and in the correct format |
| "API error: 500" | Server-side error | Check the terminal output for the backend server for detailed error messages |
| Resume upload fails | File format not supported or file is corrupted | Ensure the file is a valid PDF, DOCX, or TXT. Try saving a new copy of the file |
| Match score is 0 | Insufficient profile data or LLM response parsing error | Upload a more complete resume or add detailed projects. Check that your API key is valid |
| "Ollama not reachable" | Using local LLM but Ollama is not running | Start Ollama: `ollama serve`. Or switch to Nvidia NIM in your `.env` file |
| Empty dashboard metrics | No applications tracked yet | Add jobs and track applications first |

### 9.2 LLM Provider Issues

**Nvidia NIM (Cloud)**:

- Ensure your API key is valid and has not expired
- Check your internet connection
- Verify the API key is correctly set in the `.env` file
- The free tier has rate limits -- if you see timeout errors, wait a minute and try again

**Ollama (Local)**:

- Ensure Ollama is installed: https://ollama.ai
- Start the Ollama server: `ollama serve`
- Pull the required model: `ollama pull llama3.1:8b`
- Verify the model is running: `ollama list`
- Check that the Ollama URL in `.env` matches your setup (default: `http://localhost:11434`)

### 9.3 Database Issues

The application uses SQLite, which stores data locally. Common issues:

| Issue | Solution |
|---|---|
| "Database is locked" | Close any other processes accessing the database file. Restart the backend server. |
| Data appears lost | Check the `data/career_agent.db` file exists. If using version control, ensure `.gitignore` excludes database files. |
| Slow performance | The SQLite database may need vacuuming. Restart the backend server to release locks. |
| Corruption | Delete `data/career_agent.db` and restart the server. The database will be recreated. You will need to re-upload your resume. |

---

## 10. Frequently Asked Questions

**Q: Is my data sent to external servers?**

A: Your resume text, project details, and application data are stored locally on your machine in SQLite and ChromaDB. The only external calls are to the LLM provider (Nvidia NIM or Ollama) for AI analysis. Your data is sent as context for analysis but is not stored by the AI provider.

**Q: Can I use this without an internet connection?**

A: If you use Ollama as your LLM provider (local mode), the system can work offline after initial setup. If you use Nvidia NIM, an internet connection is required for all AI operations.

**Q: How many jobs can I track?**

A: There is no hard limit. The system uses SQLite which can handle thousands of records. Performance may slow with very large datasets, but for typical job searches (10-50 applications), performance is excellent.

**Q: Can I upload multiple resumes?**

A: Each resume upload creates a new profile. If you want to update your existing profile, upload a new resume -- the system will create a new entry. You can manage multiple profiles by changing the Profile ID in the sidebar.

**Q: What file formats are supported for resume upload?**

A: PDF (.pdf), Microsoft Word (.docx), and plain text (.txt). PDFs must be text-based (not scanned images).

**Q: How accurate are the match scores?**

A: Match scores are generated by AI analysis and should be used as one data point among many. They are most useful for comparative analysis (ranking multiple jobs against each other) rather than absolute assessment. Always apply your own judgment.

**Q: Can I export the generated resume and cover letter?**

A: Yes. The generated text appears in expandable sections on the Match & Generate tab. You can copy the text directly from the text areas and paste it into your preferred document editor for formatting.

**Q: What if the AI generates inaccurate information?**

A: The system is designed to use only information from your uploaded resume and added projects. However, AI can sometimes misinterpret or embellish details. Always review generated materials carefully and correct any inaccuracies before using them.

**Q: Can I run this on a different port?**

A: Yes. When starting the backend, use the `--port` flag: `uvicorn app.main:app --port 9000`. When starting the frontend, use: `streamlit run frontend/streamlit_app.py --server.port 9001`. Update the `BACKEND_URL` in `frontend/streamlit_app.py` if you change the backend port.

**Q: How do I switch between Nvidia NIM and local Ollama?**

A: Edit your `.env` file:

```
# For Nvidia NIM (cloud):
LLM_PROVIDER=nvidia
NVIDIA_API_KEY=your-key-here

# For Ollama (local):
LLM_PROVIDER=ollama
OLLAMA_MODEL=llama3.1:8b
```

Restart the backend server after making changes.

**Q: Is there a way to see the API documentation?**

A: Yes. With the backend running, open `http://localhost:8000/docs` in your browser. This shows the interactive API documentation powered by Swagger UI.

**Q: Can I delete a job or application?**

A: The current version does not include a delete function in the user interface. To remove data, you would need to access the SQLite database directly or reset it by deleting `data/career_agent.db` and restarting the server.

**Q: What models are recommended for local use with Ollama?**

A: `llama3.1:8b` is the default and recommended model. It has a 128K context window sufficient for most career matching tasks. Smaller models (3B, 7B) may struggle with complex JSON extraction. For best results, use `llama3.1:8b` or `llama3.1:70b`.

---

*End of User Manual*
