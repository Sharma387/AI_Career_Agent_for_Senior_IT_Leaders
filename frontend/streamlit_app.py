import streamlit as st
import httpx
import pandas as pd
from io import BytesIO

st.set_page_config(
    page_title="AI Career Agent",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded",
)

BACKEND_URL = "http://localhost:8000"

st.markdown("""
<style>
    .stMetric {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #0f3460;
    }
    .stMetric label {
        color: #e94560 !important;
        font-size: 0.9rem !important;
    }
    .stMetric [data-testid="stMetricValue"] {
        color: #ffffff !important;
        font-size: 1.8rem !important;
    }
    div[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0f0c29 0%, #302b63 50%, #24243e 100%);
    }
    div[data-testid="stSidebar"] .stMarkdown p,
    div[data-testid="stSidebar"] .stMarkdown h1,
    div[data-testid="stSidebar"] .stMarkdown h2,
    div[data-testid="stSidebar"] .stMarkdown h3,
    div[data-testid="stSidebar"] label {
        color: #ffffff !important;
    }
    .match-score-high { color: #00c853; font-weight: bold; font-size: 1.4rem; }
    .match-score-medium { color: #ffc107; font-weight: bold; font-size: 1.4rem; }
    .match-score-low { color: #ff5252; font-weight: bold; font-size: 1.4rem; }
    .status-offer { color: #00c853; font-weight: bold; }
    .status-interview { color: #ff9800; font-weight: bold; }
    .status-applied { color: #2196f3; font-weight: bold; }
    .status-rejected { color: #f44336; font-weight: bold; }
    .status-ghosted { color: #9e9e9e; font-weight: bold; }
    .status withdrawn { color: #9c27b0; font-weight: bold; }
    .block-container { padding-top: 2rem; }
    h1, h2, h3 { color: #1a1a2e; }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] {
        padding: 10px 20px;
        border-radius: 5px 5px 0 0;
    }
    .insight-card {
        background: #f8f9fa;
        border-left: 4px solid #0f3460;
        padding: 15px;
        margin: 10px 0;
        border-radius: 0 8px 8px 0;
    }
    .star-answer {
        background: #f0f4ff;
        padding: 15px;
        border-radius: 8px;
        margin: 5px 0;
        border: 1px solid #c5cae9;
    }
</style>
""", unsafe_allow_html=True)


def api_get(endpoint, params=None):
    try:
        r = httpx.get(f"{BACKEND_URL}{endpoint}", params=params, timeout=30)
        r.raise_for_status()
        return r.json()
    except httpx.ConnectError:
        st.error("Cannot connect to backend. Is the FastAPI server running at " + BACKEND_URL + "?")
        return None
    except httpx.HTTPStatusError as e:
        st.error(f"API error: {e.response.status_code} - {e.response.text}")
        return None
    except Exception as e:
        st.error(f"Request failed: {str(e)}")
        return None


def api_post(endpoint, data=None, files=None):
    try:
        r = httpx.post(f"{BACKEND_URL}{endpoint}", data=data, files=files, timeout=60)
        r.raise_for_status()
        return r.json()
    except httpx.ConnectError:
        st.error("Cannot connect to backend. Is the FastAPI server running?")
        return None
    except httpx.HTTPStatusError as e:
        st.error(f"API error: {e.response.status_code} - {e.response.text}")
        return None
    except Exception as e:
        st.error(f"Request failed: {str(e)}")
        return None


def api_put(endpoint, data=None):
    try:
        r = httpx.put(f"{BACKEND_URL}{endpoint}", json=data, timeout=30)
        r.raise_for_status()
        return r.json()
    except httpx.ConnectError:
        st.error("Cannot connect to backend.")
        return None
    except httpx.HTTPStatusError as e:
        st.error(f"API error: {e.response.status_code} - {e.response.text}")
        return None
    except Exception as e:
        st.error(f"Request failed: {str(e)}")
        return None


def format_status(status):
    status_map = {
        "offer": "🟢 Offer",
        "interview": "🟠 Interview",
        "applied": "🔵 Applied",
        "rejected": "🔴 Rejected",
        "ghosted": "⚪ Ghosted",
        "withdrawn": "🟣 Withdrawn",
    }
    return status_map.get(status.lower(), status)


def score_color(score):
    if score >= 75:
        return "match-score-high"
    elif score >= 50:
        return "match-score-medium"
    return "match-score-low"


with st.sidebar:
    st.markdown("# 💼 AI Career Agent")
    st.markdown("*Empowering Senior IT Leaders*")
    st.markdown("---")
    page = st.radio(
        "Navigation",
        ["Dashboard", "Profile", "Job Board", "Application Tracker", "Insights", "Interview Prep"],
        index=0,
    )
    st.markdown("---")
    profile_id = st.number_input("Profile ID", min_value=1, value=1, step=1)
    st.markdown("---")
    st.caption("Backend: localhost:8000")


if page == "Dashboard":
    st.title("📊 Executive Dashboard")
    st.markdown("Welcome back. Here is your career intelligence overview.")

    col1, col2, col3, col4 = st.columns(4)

    stats = api_get(f"/api/dashboard/stats/{profile_id}")

    with col1:
        total_apps = stats.get("total_applications", 0) if stats else 0
        st.metric("Total Applications", total_apps)
    with col2:
        interview_rate = stats.get("interview_rate", 0) if stats else 0
        st.metric("Interview Rate", f"{interview_rate:.1f}%")
    with col3:
        rejection_rate = stats.get("rejection_rate", 0) if stats else 0
        st.metric("Rejection Rate", f"{rejection_rate:.1f}%")
    with col4:
        avg_match = stats.get("average_match_score", 0) if stats else 0
        st.metric("Avg Match Score", f"{avg_match:.1f}%")

    st.markdown("---")

    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("Recent Applications")
        apps = api_get(f"/api/applications/list/{profile_id}")
        if apps and isinstance(apps, list) and len(apps) > 0:
            df_apps = pd.DataFrame(apps)
            display_cols = [c for c in ["id", "company", "position", "status", "applied_date"] if c in df_apps.columns]
            if display_cols:
                df_display = df_apps[display_cols].copy()
                if "status" in df_display.columns:
                    df_display["status"] = df_display["status"].apply(format_status)
                st.dataframe(df_display, use_container_width=True, hide_index=True)
            else:
                st.dataframe(df_apps, use_container_width=True, hide_index=True)
        else:
            st.info("No applications yet. Start by adding jobs and matching!")

    with col_right:
        st.subheader("Recent Match Results")
        matches = api_get(f"/api/jobs/matches/{profile_id}")
        if matches and isinstance(matches, list) and len(matches) > 0:
            df_matches = pd.DataFrame(matches)
            display_cols = [c for c in ["job_id", "company", "position", "overall_score"] if c in df_matches.columns]
            if display_cols:
                df_display = df_matches[display_cols].copy()
                if "overall_score" in df_display.columns:
                    df_display["overall_score"] = df_display["overall_score"].apply(lambda x: f"{x:.1f}%")
                st.dataframe(df_display, use_container_width=True, hide_index=True)
            else:
                st.dataframe(df_matches, use_container_width=True, hide_index=True)
        else:
            st.info("No match results yet. Match your profile against jobs!")

elif page == "Profile":
    st.title("👤 Professional Profile")
    st.markdown("Build and manage your executive profile for maximum impact.")

    tab1, tab2, tab3 = st.tabs(["Resume Upload", "Detailed Profile", "Profile Chunks"])

    with tab1:
        st.subheader("Upload Resume")
        uploaded_file = st.file_uploader(
            "Upload your resume (PDF, DOCX, or TXT)",
            type=["pdf", "docx", "txt"],
            key="resume_upload",
        )
        if uploaded_file and st.button("Upload & Process Resume", type="primary"):
            with st.spinner("Processing your resume..."):
                file_bytes = uploaded_file.read()
                files = {"file": (uploaded_file.name, BytesIO(file_bytes), uploaded_file.type)}
                result = api_post(f"/api/profile/{profile_id}/upload-resume", files=files)
                if result:
                    st.success("Resume processed successfully!")
                    st.json(result)

    with tab2:
        st.subheader("Add Detailed Project Experience")
        with st.form("project_form", clear_on_submit=True):
            cols = st.columns(2)
            with cols[0]:
                proj_title = st.text_input("Project Title *")
                proj_role = st.text_input("Your Role *")
                proj_technologies = st.text_input("Technologies Used *")
            with cols[1]:
                proj_description = st.text_area("Project Description *", height=100)
                proj_impact = st.text_area("Business Impact & Results *", height=100)

            st.markdown("**STAR Method Details**")
            star_cols = st.columns(2)
            with star_cols[0]:
                star_situation = st.text_area("Situation - Context & background", height=80)
                star_task = st.text_area("Task - Your specific responsibility", height=80)
            with star_cols[1]:
                star_action = st.text_area("Action - What you did", height=80)
                star_result = st.text_area("Result - Quantifiable outcomes", height=80)

            submitted = st.form_submit_button("Save Project", type="primary")
            if submitted:
                if not proj_title or not proj_role or not proj_technologies:
                    st.error("Please fill in all required fields (marked with *).")
                else:
                    project_data = {
                        "title": proj_title,
                        "description": proj_description,
                        "role": proj_role,
                        "technologies": proj_technologies,
                        "impact": proj_impact,
                        "star_situation": star_situation,
                        "star_task": star_task,
                        "star_action": star_action,
                        "star_result": star_result,
                    }
                    result = api_post(f"/api/profile/{profile_id}/projects", data=project_data)
                    if result:
                        st.success("Project added to your profile!")
                        st.json(result)

    with tab3:
        st.subheader("Profile Chunks")
        st.markdown("These are the processed segments of your profile used for matching.")
        chunks = api_get(f"/api/profile/{profile_id}/chunks")
        if chunks and isinstance(chunks, list) and len(chunks) > 0:
            for i, chunk in enumerate(chunks):
                with st.expander(f"Chunk {i + 1}: {chunk.get('title', chunk.get('type', 'Segment'))}", expanded=False):
                    if isinstance(chunk, dict):
                        for key, value in chunk.items():
                            if value:
                                st.markdown(f"**{key.replace('_', ' ').title()}:** {value}")
                    else:
                        st.write(chunk)
        else:
            st.info("No profile chunks available. Upload a resume or add projects to build your profile.")

elif page == "Job Board":
    st.title("💼 Job Board")
    st.markdown("Discover opportunities and generate tailored application materials.")

    tab_add, tab_list, tab_match = st.tabs(["Add Job", "All Jobs", "Match & Generate"])

    with tab_add:
        st.subheader("Add New Job Opportunity")
        with st.form("add_job_form", clear_on_submit=True):
            job_cols = st.columns(2)
            with job_cols[0]:
                job_company = st.text_input("Company *")
                job_position = st.text_input("Position Title *")
                job_location = st.text_input("Location")
                job_url = st.text_input("Job URL (optional)")
            with job_cols[1]:
                job_description = st.text_area("Full Job Description *", height=250)
                job_salary = st.text_input("Salary Range (optional)")

            submitted = st.form_submit_button("Add Job", type="primary")
            if submitted:
                if not job_company or not job_position or not job_description:
                    st.error("Company, Position, and Job Description are required.")
                else:
                    job_data = {
                        "company": job_company,
                        "position": job_position,
                        "location": job_location,
                        "url": job_url,
                        "description": job_description,
                        "salary_range": job_salary,
                    }
                    result = api_post("/api/jobs/add", data=job_data)
                    if result:
                        st.success(f"Job added: {job_company} - {job_position}")
                        st.json(result)

        st.markdown("---")
        st.subheader("Or Paste a Job Description for Quick Match")
        paste_job_desc = st.text_area("Paste job description here", height=200, key="quick_job")
        if st.button("Quick Add & Match", type="secondary"):
            if paste_job_desc.strip():
                with st.spinner("Adding job and generating match..."):
                    result = api_post("/api/jobs/add", data={"description": paste_job_desc})
                    if result:
                        job_id = result.get("id") or result.get("job_id")
                        if job_id:
                            match_result = api_post(
                                f"/api/jobs/{job_id}/match",
                                data={"profile_id": profile_id},
                            )
                            if match_result:
                                st.success("Job added and matched!")
                                st.json(match_result)
            else:
                st.warning("Please paste a job description first.")

    with tab_list:
        st.subheader("All Jobs")
        jobs = api_get("/api/jobs/list")
        if jobs and isinstance(jobs, list) and len(jobs) > 0:
            df_jobs = pd.DataFrame(jobs)
            display_cols = [c for c in ["id", "company", "position", "location", "created_at"] if c in df_jobs.columns]
            if display_cols:
                st.dataframe(df_jobs[display_cols], use_container_width=True, hide_index=True)
            else:
                st.dataframe(df_jobs, use_container_width=True, hide_index=True)
        else:
            st.info("No jobs in your board yet. Add one above!")

    with tab_match:
        st.subheader("Match Profile to Job & Generate Materials")
        jobs = api_get("/api/jobs/list")
        job_options = {}
        if jobs and isinstance(jobs, list):
            for j in jobs:
                jid = j.get("id", j.get("job_id"))
                label = f"{j.get('company', 'Unknown')} - {j.get('position', 'Unknown')} (ID: {jid})"
                job_options[label] = jid

        if job_options:
            selected_job = st.selectbox("Select a Job", list(job_options.keys()))
            selected_job_id = job_options[selected_job]

            match_cols = st.columns(2)
            with match_cols[0]:
                if st.button("Run Match Analysis", type="primary"):
                    with st.spinner("Analyzing match..."):
                        match_result = api_post(
                            f"/api/jobs/{selected_job_id}/match",
                            data={"profile_id": profile_id},
                        )
                        if match_result:
                            st.session_state["last_match"] = match_result

            with match_cols[1]:
                if st.button("Generate Resume & Cover Letter", type="primary"):
                    with st.spinner("Generating tailored materials..."):
                        gen_result = api_post(
                            f"/api/jobs/{selected_job_id}/generate",
                            data={"profile_id": profile_id},
                        )
                        if gen_result:
                            st.session_state["last_generation"] = gen_result

            if "last_match" in st.session_state:
                st.markdown("---")
                st.subheader("Match Analysis Results")
                match = st.session_state["last_match"]
                score = match.get("overall_score", match.get("score", 0))
                css_class = score_color(score)
                st.markdown(f'<div class="{css_class}">Overall Match Score: {score:.1f}%</div>', unsafe_allow_html=True)

                progress_val = score / 100.0 if score <= 1 else score
                st.progress(progress_val)

                if match.get("strengths"):
                    st.markdown("**✅ Strengths**")
                    for s in (match["strengths"] if isinstance(match["strengths"], list) else [match["strengths"]]):
                        st.markdown(f"- {s}")

                if match.get("gaps"):
                    st.markdown("**⚠️ Gaps to Address**")
                    for g in (match["gaps"] if isinstance(match["gaps"], list) else [match["gaps"]]):
                        st.markdown(f"- {g}")

                if match.get("evidence"):
                    st.markdown("**📋 Evidence**")
                    for e in (match["evidence"] if isinstance(match["evidence"], list) else [match["evidence"]]):
                        st.markdown(f"- {e}")

                if match.get("explanation"):
                    st.markdown("**💡 Explanation**")
                    st.info(match["explanation"])

                if match.get("recommendations"):
                    st.markdown("**🎯 Recommendations**")
                    for r in (match["recommendations"] if isinstance(match["recommendations"], list) else [match["recommendations"]]):
                        st.markdown(f"- {r}")

            if "last_generation" in st.session_state:
                st.markdown("---")
                st.subheader("Generated Application Materials")
                gen = st.session_state["last_generation"]

                if gen.get("resume") or gen.get("tailored_resume"):
                    resume_text = gen.get("resume") or gen.get("tailored_resume")
                    with st.expander("📄 Tailored Resume", expanded=True):
                        st.text_area("Resume", resume_text, height=400, disabled=True, key="resume_display")

                if gen.get("cover_letter") or gen.get("tailored_cover_letter"):
                    cl_text = gen.get("cover_letter") or gen.get("tailored_cover_letter")
                    with st.expander("✉️ Cover Letter", expanded=True):
                        st.text_area("Cover Letter", cl_text, height=300, disabled=True, key="cl_display")

                if gen.get("key Talking Points") or gen.get("talking_points"):
                    tp = gen.get("key Talking Points") or gen.get("talking_points")
                    with st.expander("🗣️ Key Talking Points"):
                        st.markdown(tp)
        else:
            st.info("Add some jobs first before matching.")

elif page == "Application Tracker":
    st.title("📋 Application Tracker")
    st.markdown("Track every opportunity from first touch to final decision.")

    tab_track, tab_update, tab_funnel = st.tabs(["Track Application", "Update Status", "Funnel View"])

    with tab_track:
        st.subheader("Track New Application")
        jobs = api_get("/api/jobs/list")
        job_options = {}
        if jobs and isinstance(jobs, list):
            for j in jobs:
                jid = j.get("id", j.get("job_id"))
                label = f"{j.get('company', 'Unknown')} - {j.get('position', 'Unknown')} (ID: {jid})"
                job_options[label] = jid

        if job_options:
            with st.form("track_app_form", clear_on_submit=True):
                selected_job = st.selectbox("Select Job *", list(job_options.keys()))
                app_status = st.selectbox("Initial Status *", ["applied", "interview", "offer", "rejected", "ghosted", "withdrawn"])
                notes = st.text_area("Notes (optional)")
                submitted = st.form_submit_button("Track Application", type="primary")
                if submitted:
                    result = api_post(
                        f"/api/applications/{profile_id}/track",
                        data={"job_id": job_options[selected_job], "status": app_status, "notes": notes},
                    )
                    if result:
                        st.success("Application tracked!")
                        st.json(result)
        else:
            st.info("Add jobs to the board first before tracking applications.")

    with tab_update:
        st.subheader("Update Application Status")
        apps = api_get(f"/api/applications/list/{profile_id}")
        if apps and isinstance(apps, list) and len(apps) > 0:
            app_options = {}
            for a in apps:
                aid = a.get("id", a.get("application_id"))
                label = f"#{aid} - {a.get('company', 'Unknown')} - {a.get('position', 'Unknown')} [{a.get('status', 'unknown')}]"
                app_options[label] = aid

            with st.form("update_app_form"):
                selected_app = st.selectbox("Select Application", list(app_options.keys()))
                new_status = st.selectbox("New Status", ["applied", "interview", "offer", "rejected", "ghosted", "withdrawn"])
                feedback = st.text_area("Feedback Notes (optional)")
                updated = st.form_submit_button("Update Status", type="primary")
                if updated:
                    result = api_put(
                        f"/api/applications/{app_options[selected_app]}/status",
                        data={"status": new_status, "feedback": feedback},
                    )
                    if result:
                        st.success("Status updated!")
                        st.json(result)
        else:
            st.info("No applications to update yet.")

    with tab_funnel:
        st.subheader("Application Funnel")
        apps = api_get(f"/api/applications/list/{profile_id}")
        if apps and isinstance(apps, list) and len(apps) > 0:
            df_apps = pd.DataFrame(apps)
            if "status" in df_apps.columns:
                status_counts = df_apps["status"].value_counts()

                funnel_order = ["applied", "interview", "offer", "rejected", "ghosted", "withdrawn"]
                funnel_data = []
                for s in funnel_order:
                    if s in status_counts.index:
                        funnel_data.append({"Status": format_status(s), "Count": int(status_counts[s])})

                if funnel_data:
                    df_funnel = pd.DataFrame(funnel_data)
                    st.bar_chart(df_funnel.set_index("Status"))

                    total = len(df_apps)
                    st.markdown("**Conversion Rates:**")
                    applied_count = int(status_counts.get("applied", 0))
                    interview_count = int(status_counts.get("interview", 0))
                    offer_count = int(status_counts.get("offer", 0))
                    rejected_count = int(status_counts.get("rejected", 0))

                    rate_cols = st.columns(4)
                    with rate_cols[0]:
                        st.metric("Applied → Interview", f"{(interview_count / total * 100):.1f}%" if total else "0%")
                    with rate_cols[1]:
                        st.metric("Interview → Offer", f"{(offer_count / interview_count * 100):.1f}%" if interview_count else "0%")
                    with rate_cols[2]:
                        st.metric("Overall Success", f"{(offer_count / total * 100):.1f}%" if total else "0%")
                    with rate_cols[3]:
                        st.metric("Rejection Rate", f"{(rejected_count / total * 100):.1f}%" if total else "0%")

                    st.markdown("---")
                    st.subheader("All Applications")
                    display_cols = [c for c in ["id", "company", "position", "status", "applied_date", "notes"] if c in df_apps.columns]
                    df_display = df_apps[display_cols].copy() if display_cols else df_apps.copy()
                    if "status" in df_display.columns:
                        df_display["status"] = df_display["status"].apply(format_status)
                    st.dataframe(df_display, use_container_width=True, hide_index=True)
                else:
                    st.info("No applications with trackable statuses.")
            else:
                st.info("Application data does not include status field.")
        else:
            st.info("No applications to visualize. Start tracking your applications!")

elif page == "Insights":
    st.title("🧠 Career Intelligence Insights")
    st.markdown("AI-powered analysis of your job search performance.")

    if st.button("Generate Insights", type="primary"):
        with st.spinner("Analyzing your career data..."):
            insights = api_get(f"/api/insights/{profile_id}")
            if insights:
                st.session_state["insights"] = insights

    if "insights" in st.session_state:
        ins = st.session_state["insights"]

        if ins.get("rejection_patterns"):
            st.subheader("🔴 Rejection Patterns")
            patterns = ins["rejection_patterns"]
            if isinstance(patterns, list):
                for p in patterns:
                    st.markdown(f'<div class="insight-card">{p}</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="insight-card">{patterns}</div>', unsafe_allow_html=True)

        if ins.get("success_patterns"):
            st.subheader("🟢 Success Patterns")
            patterns = ins["success_patterns"]
            if isinstance(patterns, list):
                for p in patterns:
                    st.markdown(f'<div class="insight-card">{p}</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="insight-card">{patterns}</div>', unsafe_allow_html=True)

        if ins.get("improvement_suggestions"):
            st.subheader("💡 Improvement Suggestions")
            suggestions = ins["improvement_suggestions"]
            if isinstance(suggestions, list):
                for s in suggestions:
                    st.markdown(f'<div class="insight-card">{s}</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="insight-card">{suggestions}</div>', unsafe_allow_html=True)

        if ins.get("interview_conversion_rate") is not None:
            st.subheader("📈 Interview Conversion Rate")
            conv_rate = ins["interview_conversion_rate"]
            st.metric("Conversion Rate", f"{conv_rate:.1f}%")
            st.progress(conv_rate / 100.0)

        if ins.get("key_insights"):
            st.subheader("🔑 Key Insights")
            key = ins["key_insights"]
            if isinstance(key, list):
                for k in key:
                    st.info(k)
            else:
                st.info(str(key))

        if ins.get("recommendations"):
            st.subheader("🎯 Recommendations")
            recs = ins["recommendations"]
            if isinstance(recs, list):
                for r in recs:
                    st.warning(r)
            else:
                st.warning(str(recs))

        with st.expander("View Raw Insights Data"):
            st.json(ins)
    else:
        st.info("Click 'Generate Insights' to analyze your career data.")

elif page == "Interview Prep":
    st.title("🎤 Interview Preparation")
    st.markdown("AI-powered interview coaching tailored to each opportunity.")

    jobs = api_get("/api/jobs/list")
    job_options = {}
    if jobs and isinstance(jobs, list):
        for j in jobs:
            jid = j.get("id", j.get("job_id"))
            label = f"{j.get('company', 'Unknown')} - {j.get('position', 'Unknown')} (ID: {jid})"
            job_options[label] = jid

    if job_options:
        selected_job = st.selectbox("Select Job for Interview Prep", list(job_options.keys()))
        selected_job_id = job_options[selected_job]

        if st.button("Generate Interview Prep", type="primary"):
            with st.spinner("Preparing your interview materials..."):
                prep = api_post(
                    f"/api/interview-prep/{selected_job_id}",
                    data={"profile_id": profile_id},
                )
                if prep:
                    st.session_state["interview_prep"] = prep

        if "interview_prep" in st.session_state:
            prep = st.session_state["interview_prep"]

            if prep.get("likely_questions") or prep.get("questions"):
                questions = prep.get("likely_questions") or prep.get("questions")
                st.subheader("Likely Interview Questions")
                if isinstance(questions, list):
                    for i, q in enumerate(questions):
                        question_text = q.get("question", q) if isinstance(q, dict) else str(q)
                        answer_text = q.get("answer", q.get("star_answer", "")) if isinstance(q, dict) else ""
                        with st.expander(f"Q{i + 1}: {question_text}", expanded=False):
                            if answer_text:
                                st.markdown("**Recommended STAR Response:**")
                                if isinstance(answer_text, dict):
                                    for star_key in ["situation", "task", "action", "result"]:
                                        if answer_text.get(star_key):
                                            st.markdown(f"**{star_key.title()}:** {answer_text[star_key]}")
                                else:
                                    st.markdown(f'<div class="star-answer">{answer_text}</div>', unsafe_allow_html=True)
                            else:
                                st.info("No pre-generated answer. Practice using the STAR method.")
                elif isinstance(questions, dict):
                    for q_key, q_val in questions.items():
                        with st.expander(f"Q: {q_key}", expanded=False):
                            if isinstance(q_val, dict):
                                for k, v in q_val.items():
                                    st.markdown(f"**{k.title()}:** {v}")
                            else:
                                st.markdown(str(q_val))
                else:
                    st.write(questions)

            if prep.get("talking_points"):
                st.subheader("🗣️ Key Talking Points")
                tp = prep["talking_points"]
                if isinstance(tp, list):
                    for t in tp:
                        st.markdown(f"- {t}")
                else:
                    st.markdown(str(tp))

            if prep.get("company_research"):
                st.subheader("🏢 Company Research Notes")
                cr = prep["company_research"]
                if isinstance(cr, dict):
                    for k, v in cr.items():
                        st.markdown(f"**{k}:** {v}")
                else:
                    st.markdown(str(cr))

            if prep.get("strategy"):
                st.subheader("🎯 Interview Strategy")
                st.info(str(prep["strategy"]))

            with st.expander("View Full Prep Data"):
                st.json(prep)
    else:
        st.info("Add jobs to the board first to generate interview prep materials.")
