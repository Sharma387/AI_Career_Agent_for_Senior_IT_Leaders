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
    .stMetric label { color: #e94560 !important; font-size: 0.9rem !important; }
    .stMetric [data-testid="stMetricValue"] { color: #ffffff !important; font-size: 1.8rem !important; }
    div[data-testid="stSidebar"] { background: linear-gradient(180deg, #0f0c29 0%, #302b63 50%, #24243e 100%); }
    div[data-testid="stSidebar"] .stMarkdown p,
    div[data-testid="stSidebar"] .stMarkdown h1,
    div[data-testid="stSidebar"] .stMarkdown h2,
    div[data-testid="stSidebar"] .stMarkdown h3,
    div[data-testid="stSidebar"] label { color: #ffffff !important; }
    .match-score-high { color: #00c853; font-weight: bold; font-size: 1.4rem; }
    .match-score-medium { color: #ffc107; font-weight: bold; font-size: 1.4rem; }
    .match-score-low { color: #ff5252; font-weight: bold; font-size: 1.4rem; }
    .block-container { padding-top: 2rem; }
    h1, h2, h3 { color: #1a1a2e; }
</style>
""", unsafe_allow_html=True)


def api_get(endpoint, params=None):
    try:
        r = httpx.get(f"{BACKEND_URL}{endpoint}", params=params, timeout=30)
        r.raise_for_status()
        return r.json()
    except httpx.ConnectError:
        st.error("Cannot connect to backend. Is FastAPI running at " + BACKEND_URL + "?")
        return None
    except httpx.HTTPStatusError as e:
        st.error(f"API error: {e.response.status_code} - {e.response.text}")
        return None
    except Exception as e:
        st.error(f"Request failed: {e}")
        return None


def api_post(endpoint, data=None, files=None, params=None):
    try:
        r = httpx.post(f"{BACKEND_URL}{endpoint}", data=data, files=files, params=params, timeout=120)
        r.raise_for_status()
        return r.json()
    except httpx.ConnectError:
        st.error("Cannot connect to backend.")
        return None
    except httpx.HTTPStatusError as e:
        st.error(f"API error: {e.response.status_code} - {e.response.text}")
        return None
    except Exception as e:
        st.error(f"Request failed: {e}")
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
        st.error(f"Request failed: {e}")
        return None


def format_status(status):
    s = str(status).lower()
    colors = {"applied": "blue", "phone_screen": "orange", "technical_interview": "orange",
              "final_interview": "orange", "offered": "green", "rejected": "red",
              "withdrawn": "purple", "accepted": "green", "reviewing": "gray"}
    color = colors.get(s, "gray")
    return f":{color}[{s.replace('_', ' ').title()}]"


with st.sidebar:
    st.markdown("# AI Career Agent")
    st.markdown("*Empowering Senior IT Leaders*")
    st.markdown("---")
    page = st.radio(
        "Navigation",
        ["Dashboard", "Profile", "Job Board", "Application Tracker", "Insights", "Interview Prep"],
        index=0,
    )
    st.markdown("---")
    profile_id = st.number_input("Profile ID", min_value=1, value=1, step=1)
    st.caption("Backend: localhost:8000")


if page == "Dashboard":
    st.title("Executive Dashboard")

    col1, col2, col3, col4 = st.columns(4)
    stats = api_get(f"/api/applications/stats/{profile_id}")

    with col1:
        st.metric("Total Applications", stats.get("total_applied", 0) if stats else 0)
    with col2:
        st.metric("Interview Rate", f"{stats.get('interview_rate', 0):.1f}%" if stats else "0%")
    with col3:
        st.metric("Rejection Rate", f"{100 - stats.get('interview_rate', 0) - stats.get('success_rate', 0):.1f}%" if stats else "0%")
    with col4:
        st.metric("Success Rate", f"{stats.get('success_rate', 0):.1f}%" if stats else "0%")

    st.markdown("---")
    st.subheader("Recent Applications")
    apps = api_get(f"/api/applications/{profile_id}")
    if apps and len(apps) > 0:
        rows = []
        for a in apps:
            job = a.get("job") or {}
            rows.append({
                "ID": a.get("application_id"),
                "Company": job.get("company", ""),
                "Position": job.get("title", ""),
                "Status": a.get("status", ""),
                "Applied": a.get("date_applied", "")[:10] if a.get("date_applied") else "",
            })
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No applications yet. Add jobs and start matching!")

elif page == "Profile":
    st.title("Professional Profile")

    tab1, tab2 = st.tabs(["Resume Upload", "Add Project"])

    with tab1:
        st.subheader("Upload Resume")
        uploaded_file = st.file_uploader("Upload resume (PDF, DOCX, or TXT)", type=["pdf", "docx", "txt"])
        if uploaded_file and st.button("Upload & Process", type="primary"):
            with st.spinner("Processing resume..."):
                files = {"file": (uploaded_file.name, BytesIO(uploaded_file.read()), uploaded_file.type)}
                result = api_post("/api/profile/upload-resume", files=files)
                if result:
                    st.success("Resume processed!")
                    st.json(result)

    with tab2:
        st.subheader("Add Detailed Project")
        with st.form("project_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                title = st.text_input("Project Title *")
                role = st.text_input("Your Role *")
                technologies = st.text_input("Technologies *")
            with c2:
                description = st.text_area("Description *", height=100)
                impact = st.text_area("Impact *", height=100)

            st.markdown("**STAR Method**")
            sc1, sc2 = st.columns(2)
            with sc1:
                star_situation = st.text_area("Situation", height=80)
                star_task = st.text_area("Task", height=80)
            with sc2:
                star_action = st.text_area("Action", height=80)
                star_result = st.text_area("Result", height=80)

            if st.form_submit_button("Save Project", type="primary"):
                if not title:
                    st.error("Title is required.")
                else:
                    result = api_post(f"/api/profile/{profile_id}/project", data={
                        "title": title, "description": description, "role": role,
                        "technologies": technologies, "impact": impact,
                        "star_situation": star_situation, "star_task": star_task,
                        "star_action": star_action, "star_result": star_result,
                    })
                    if result:
                        st.success("Project added!")

elif page == "Job Board":
    st.title("Job Board")

    tab_add, tab_list, tab_match = st.tabs(["Add Job", "All Jobs", "Match & Generate"])

    with tab_add:
        st.subheader("Add Job (paste description)")
        job_text = st.text_area("Paste full job description", height=300)
        if st.button("Add Job", type="primary"):
            if job_text.strip():
                result = api_post("/api/jobs/add", data={"text": job_text})
                if result:
                    st.success(f"Job added! ID: {result.get('job_id')}")
                    st.json(result.get("parsed_data", {}))
            else:
                st.warning("Paste a job description first.")

    with tab_list:
        st.subheader("All Jobs")
        jobs = api_get("/api/jobs")
        if jobs and len(jobs) > 0:
            df = pd.DataFrame(jobs)
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("No jobs yet.")

    with tab_match:
        st.subheader("Match & Generate Materials")
        jobs = api_get("/api/jobs")
        job_map = {}
        if jobs:
            for j in jobs:
                label = f"{j.get('company', '?')} - {j.get('title', '?')} (ID: {j['id']})"
                job_map[label] = j["id"]

        if job_map:
            selected = st.selectbox("Select Job", list(job_map.keys()))
            job_id = job_map[selected]

            c1, c2 = st.columns(2)
            with c1:
                if st.button("Run Match", type="primary"):
                    with st.spinner("Matching..."):
                        result = api_post(f"/api/jobs/{job_id}/match", params={"profile_id": profile_id})
                        if result:
                            st.session_state["last_match"] = result

            with c2:
                if st.button("Generate Resume & Cover Letter", type="primary"):
                    with st.spinner("Generating..."):
                        result = api_post(f"/api/jobs/{job_id}/generate-materials", params={"profile_id": profile_id})
                        if result:
                            st.session_state["last_gen"] = result

            if "last_match" in st.session_state:
                st.markdown("---")
                m = st.session_state["last_match"]
                score = m.get("match_score", 0)
                css = "match-score-high" if score >= 75 else "match-score-medium" if score >= 50 else "match-score-low"
                st.markdown(f'<div class="{css}">Match Score: {score}%</div>', unsafe_allow_html=True)
                st.progress(score / 100.0)

                if m.get("strengths"):
                    st.markdown("**Strengths**")
                    for s in m["strengths"]:
                        st.markdown(f"- {s}")
                if m.get("gaps"):
                    st.markdown("**Gaps**")
                    for g in m["gaps"]:
                        st.markdown(f"- {g}")
                if m.get("explanation"):
                    st.info(m["explanation"])
                if m.get("recommendation"):
                    st.success(f"Recommendation: {m['recommendation'].replace('_', ' ').title()}")

            if "last_gen" in st.session_state:
                st.markdown("---")
                g = st.session_state["last_gen"]
                if g.get("resume"):
                    with st.expander("Tailored Resume", expanded=True):
                        st.text_area("Resume", g["resume"], height=400, disabled=True)
                if g.get("cover_letter"):
                    with st.expander("Cover Letter", expanded=True):
                        st.text_area("Cover Letter", g["cover_letter"], height=300, disabled=True)
        else:
            st.info("Add jobs first.")

elif page == "Application Tracker":
    st.title("Application Tracker")

    tab_track, tab_update, tab_funnel = st.tabs(["Track Application", "Update Status", "Funnel View"])

    with tab_track:
        st.subheader("Track New Application")
        jobs = api_get("/api/jobs")
        job_map = {}
        if jobs:
            for j in jobs:
                label = f"{j.get('company', '?')} - {j.get('title', '?')} (ID: {j['id']})"
                job_map[label] = j["id"]

        if job_map:
            with st.form("track_form", clear_on_submit=True):
                selected = st.selectbox("Select Job", list(job_map.keys()))
                status = st.selectbox("Status", ["applied", "reviewing", "phone_screen", "technical_interview", "final_interview", "offered", "rejected", "withdrawn"])
                if st.form_submit_button("Track", type="primary"):
                    result = api_post("/api/applications/track", data={
                        "job_id": job_map[selected], "profile_id": profile_id, "status": status
                    })
                    if result:
                        st.success("Application tracked!")
        else:
            st.info("Add jobs first.")

    with tab_update:
        st.subheader("Update Status")
        apps = api_get(f"/api/applications/{profile_id}")
        if apps:
            app_map = {}
            for a in apps:
                job = a.get("job") or {}
                label = f"#{a['application_id']} - {job.get('company', '?')} [{a['status']}]"
                app_map[label] = a["application_id"]

            with st.form("update_form"):
                selected = st.selectbox("Select Application", list(app_map.keys()))
                new_status = st.selectbox("New Status", ["applied", "reviewing", "phone_screen", "technical_interview", "final_interview", "offered", "rejected", "withdrawn"])
                feedback = st.text_area("Feedback (optional)")
                if st.form_submit_button("Update", type="primary"):
                    result = api_put(f"/api/applications/{app_map[selected]}/status", data={
                        "new_status": new_status, "feedback": feedback
                    })
                    if result:
                        st.success("Updated!")
        else:
            st.info("No applications to update.")

    with tab_funnel:
        st.subheader("Funnel")
        apps = api_get(f"/api/applications/{profile_id}")
        if apps:
            statuses = [a.get("status", "") for a in apps]
            counts = pd.Series(statuses).value_counts()
            st.bar_chart(counts)

            stats = api_get(f"/api/applications/stats/{profile_id}")
            if stats:
                rc1, rc2, rc3 = st.columns(3)
                with rc1:
                    st.metric("Applied", stats.get("total_applied", 0))
                with rc2:
                    st.metric("Interview Rate", f"{stats.get('interview_rate', 0):.1f}%")
                with rc3:
                    st.metric("Success Rate", f"{stats.get('success_rate', 0):.1f}%")
        else:
            st.info("No data yet.")

elif page == "Insights":
    st.title("Career Intelligence Insights")

    if st.button("Generate Insights", type="primary"):
        with st.spinner("Analyzing..."):
            insights = api_get(f"/api/applications/{profile_id}/insights")
            if insights:
                st.session_state["insights"] = insights

    if "insights" in st.session_state:
        ins = st.session_state["insights"]
        for key, label in [
            ("rejection_patterns", "Rejection Patterns"),
            ("success_patterns", "Success Patterns"),
            ("improvement_suggestions", "Improvement Suggestions"),
            ("insights", "Key Insights"),
        ]:
            if ins.get(key):
                st.subheader(label)
                items = ins[key] if isinstance(ins[key], list) else [ins[key]]
                for item in items:
                    st.markdown(f"- {item}")

        if ins.get("interview_conversion_rate") is not None:
            st.metric("Interview Conversion Rate", f"{ins['interview_conversion_rate']:.1f}%")

        with st.expander("Raw Data"):
            st.json(ins)
    else:
        st.info("Click 'Generate Insights' to analyze your data.")

elif page == "Interview Prep":
    st.title("Interview Preparation")

    jobs = api_get("/api/jobs")
    job_map = {}
    if jobs:
        for j in jobs:
            label = f"{j.get('company', '?')} - {j.get('title', '?')} (ID: {j['id']})"
            job_map[label] = j["id"]

    if job_map:
        selected = st.selectbox("Select Job", list(job_map.keys()))
        job_id = job_map[selected]

        if st.button("Generate Interview Prep", type="primary"):
            with st.spinner("Generating..."):
                # Use the agent directly via match endpoint to get career context
                # Then generate prep via a dedicated endpoint (future)
                # For now, show match explanation as prep
                result = api_post(f"/api/jobs/{job_id}/match", params={"profile_id": profile_id})
                if result:
                    st.session_state["prep"] = result

        if "prep" in st.session_state:
            p = st.session_state["prep"]
            st.subheader("Match Analysis (Interview Focus)")
            if p.get("strengths"):
                st.markdown("**Your Strengths for This Role:**")
                for s in p["strengths"]:
                    st.markdown(f"- {s}")
            if p.get("explanation"):
                st.info(p["explanation"])
            if p.get("gaps"):
                st.warning("**Prepare to address these gaps:**")
                for g in p["gaps"]:
                    st.markdown(f"- {g}")
    else:
        st.info("Add jobs first.")
