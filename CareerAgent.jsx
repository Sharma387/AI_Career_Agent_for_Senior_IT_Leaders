import { useState, useRef, useCallback } from "react";

// ─── Styles ───────────────────────────────────────────────────────────────────
const styles = `
  @import url('https://fonts.googleapis.com/css2?family=Sora:wght@300;400;600;700;800&family=Inter:wght@300;400;500;600&family=JetBrains+Mono:wght@400;500&display=swap');

  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

  :root {
    --bg:       #080C18;
    --surface:  #0E1628;
    --panel:    #131B2E;
    --border:   #1E2D4A;
    --blue:     #3B82F6;
    --blue-dim: #1D3A6E;
    --gold:     #F59E0B;
    --gold-dim: #6B4A12;
    --green:    #10B981;
    --red:      #EF4444;
    --purple:   #8B5CF6;
    --text:     #E2E8F0;
    --muted:    #64748B;
    --dim:      #94A3B8;
    --font-display: 'Sora', sans-serif;
    --font-body:    'Inter', sans-serif;
    --font-mono:    'JetBrains Mono', monospace;
  }

  body { background: var(--bg); color: var(--text); font-family: var(--font-body); }

  .app { display: flex; min-height: 100vh; }

  /* ── Sidebar ── */
  .sidebar {
    width: 240px; min-height: 100vh; background: var(--surface);
    border-right: 1px solid var(--border); display: flex; flex-direction: column;
    padding: 24px 0; position: fixed; top: 0; left: 0; z-index: 100;
  }
  .sidebar-logo {
    padding: 0 20px 24px; border-bottom: 1px solid var(--border);
    font-family: var(--font-display); font-weight: 800; font-size: 18px; letter-spacing: -0.5px;
  }
  .sidebar-logo span { color: var(--blue); }
  .sidebar-logo small { display: block; font-size: 10px; color: var(--muted); font-weight: 400; letter-spacing: 2px; text-transform: uppercase; margin-top: 2px; }
  .nav-section { padding: 20px 12px 8px; font-size: 10px; color: var(--muted); letter-spacing: 2px; text-transform: uppercase; }
  .nav-item {
    display: flex; align-items: center; gap: 10px; padding: 10px 20px;
    cursor: pointer; border-radius: 0; transition: all .15s; font-size: 14px;
    color: var(--dim); border-left: 3px solid transparent; margin: 1px 0;
  }
  .nav-item:hover { background: var(--panel); color: var(--text); }
  .nav-item.active { background: var(--blue-dim); color: var(--blue); border-left-color: var(--blue); }
  .nav-item .icon { width: 18px; text-align: center; flex-shrink: 0; }
  .nav-badge {
    margin-left: auto; background: var(--blue); color: #fff;
    font-size: 10px; padding: 2px 6px; border-radius: 10px; font-family: var(--font-mono);
  }
  .sidebar-footer { margin-top: auto; padding: 16px 20px; border-top: 1px solid var(--border); }
  .status-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--green); display: inline-block; margin-right: 8px; animation: pulse-green 2s infinite; }
  @keyframes pulse-green { 0%,100%{box-shadow:0 0 0 0 rgba(16,185,129,.4)} 50%{box-shadow:0 0 0 6px rgba(16,185,129,0)} }

  /* ── Main ── */
  .main { margin-left: 240px; flex: 1; padding: 32px; min-height: 100vh; }
  .topbar { display: flex; align-items: center; justify-content: space-between; margin-bottom: 32px; }
  .page-title { font-family: var(--font-display); font-size: 26px; font-weight: 700; letter-spacing: -0.5px; }
  .page-title span { color: var(--blue); }
  .topbar-actions { display: flex; gap: 10px; }

  /* ── Buttons ── */
  .btn {
    display: inline-flex; align-items: center; gap: 7px; padding: 9px 18px;
    border-radius: 6px; font-size: 13px; font-weight: 600; cursor: pointer;
    border: none; font-family: var(--font-body); transition: all .15s; white-space: nowrap;
  }
  .btn-primary { background: var(--blue); color: #fff; }
  .btn-primary:hover { background: #2563EB; transform: translateY(-1px); box-shadow: 0 4px 16px rgba(59,130,246,.3); }
  .btn-secondary { background: var(--panel); color: var(--dim); border: 1px solid var(--border); }
  .btn-secondary:hover { color: var(--text); border-color: var(--blue); }
  .btn-gold { background: var(--gold); color: #000; }
  .btn-gold:hover { background: #D97706; transform: translateY(-1px); }
  .btn-ghost { background: transparent; color: var(--dim); border: 1px solid var(--border); }
  .btn-ghost:hover { border-color: var(--blue); color: var(--blue); }
  .btn-danger { background: transparent; color: var(--red); border: 1px solid var(--red); }
  .btn-danger:hover { background: var(--red); color: #fff; }
  .btn:disabled { opacity: .5; cursor: not-allowed; transform: none; }
  .btn-sm { padding: 6px 12px; font-size: 12px; }
  .btn-lg { padding: 12px 24px; font-size: 15px; }

  /* ── Cards / Panels ── */
  .card {
    background: var(--panel); border: 1px solid var(--border);
    border-radius: 10px; padding: 24px;
  }
  .card-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 20px; }
  .card-title { font-family: var(--font-display); font-size: 15px; font-weight: 600; }
  .card-sub { font-size: 12px; color: var(--muted); margin-top: 2px; }

  /* ── Upload zone ── */
  .upload-zone {
    border: 2px dashed var(--border); border-radius: 10px; padding: 48px 24px;
    text-align: center; cursor: pointer; transition: all .2s; position: relative;
  }
  .upload-zone:hover, .upload-zone.drag { border-color: var(--blue); background: rgba(59,130,246,.05); }
  .upload-icon { font-size: 40px; margin-bottom: 12px; }
  .upload-zone h3 { font-family: var(--font-display); font-size: 16px; font-weight: 600; margin-bottom: 6px; }
  .upload-zone p { color: var(--muted); font-size: 13px; }
  .upload-zone input { position: absolute; inset: 0; opacity: 0; cursor: pointer; }

  /* ── Resume parsed view ── */
  .resume-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
  .resume-section { background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 16px; }
  .resume-section h4 { font-size: 11px; letter-spacing: 2px; text-transform: uppercase; color: var(--muted); margin-bottom: 12px; }
  .skill-chip {
    display: inline-block; padding: 4px 10px; background: var(--blue-dim);
    color: var(--blue); border-radius: 20px; font-size: 12px; margin: 3px; font-weight: 500;
  }
  .skill-chip.soft { background: rgba(139,92,246,.15); color: var(--purple); }
  .exp-item { margin-bottom: 14px; padding-bottom: 14px; border-bottom: 1px solid var(--border); }
  .exp-item:last-child { border-bottom: none; margin-bottom: 0; padding-bottom: 0; }
  .exp-title { font-weight: 600; font-size: 14px; }
  .exp-meta { font-size: 12px; color: var(--muted); margin-top: 2px; }

  /* ── Jobs section ── */
  .job-input-area {
    background: var(--surface); border: 1px solid var(--border); border-radius: 8px;
    padding: 16px; font-family: var(--font-body); font-size: 13px; color: var(--text);
    width: 100%; min-height: 160px; resize: vertical; outline: none; transition: border .15s;
    line-height: 1.6;
  }
  .job-input-area:focus { border-color: var(--blue); }
  .job-list { display: flex; flex-direction: column; gap: 12px; margin-top: 16px; }
  .job-card {
    background: var(--surface); border: 1px solid var(--border); border-radius: 8px;
    padding: 16px; display: flex; align-items: flex-start; gap: 16px; cursor: pointer;
    transition: all .15s;
  }
  .job-card:hover { border-color: var(--blue); }
  .job-card.selected { border-color: var(--blue); background: rgba(59,130,246,.05); }
  .job-card-body { flex: 1; }
  .job-title { font-weight: 600; font-size: 15px; }
  .job-company { color: var(--muted); font-size: 13px; margin-top: 2px; }
  .job-snippet { font-size: 12px; color: var(--dim); margin-top: 8px; line-height: 1.5; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
  .job-score-badge {
    flex-shrink: 0; width: 52px; height: 52px; border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-family: var(--font-display); font-size: 17px; font-weight: 700;
    border: 2.5px solid; position: relative;
  }
  .score-high { border-color: var(--green); color: var(--green); background: rgba(16,185,129,.1); }
  .score-med  { border-color: var(--gold);  color: var(--gold);  background: rgba(245,158,11,.1); }
  .score-low  { border-color: var(--red);   color: var(--red);   background: rgba(239,68,68,.1); }
  .score-none { border-color: var(--border); color: var(--muted); background: var(--panel); }

  /* ── Evaluation panel ── */
  .eval-grid { display: grid; grid-template-columns: 280px 1fr; gap: 20px; }
  .score-ring-wrap { display: flex; flex-direction: column; align-items: center; gap: 16px; }
  .score-ring {
    width: 160px; height: 160px; border-radius: 50%; position: relative;
    display: flex; align-items: center; justify-content: center;
    font-family: var(--font-display);
  }
  .score-ring svg { position: absolute; inset: 0; transform: rotate(-90deg); }
  .score-ring-num { font-size: 38px; font-weight: 800; z-index: 1; }
  .score-ring-label { font-size: 11px; color: var(--muted); z-index: 1; letter-spacing: 1px; }

  .eval-section { margin-bottom: 20px; }
  .eval-section h4 {
    font-size: 11px; letter-spacing: 2px; text-transform: uppercase; color: var(--muted);
    margin-bottom: 12px; display: flex; align-items: center; gap: 8px;
  }
  .eval-section h4::after { content:''; flex: 1; height: 1px; background: var(--border); }
  .eval-item { display: flex; align-items: flex-start; gap: 10px; margin-bottom: 10px; font-size: 13px; line-height: 1.5; }
  .eval-dot { width: 7px; height: 7px; border-radius: 50%; margin-top: 5px; flex-shrink: 0; }

  .missing-check {
    background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 14px 16px;
    margin-bottom: 10px; display: flex; align-items: center; gap: 12px; cursor: pointer; transition: all .15s;
  }
  .missing-check:hover { border-color: var(--gold); }
  .missing-check.checked { border-color: var(--green); background: rgba(16,185,129,.05); }
  .check-box {
    width: 22px; height: 22px; border-radius: 5px; border: 2px solid var(--border);
    display: flex; align-items: center; justify-content: center; flex-shrink: 0; transition: all .15s;
  }
  .missing-check.checked .check-box { border-color: var(--green); background: var(--green); }
  .check-label { font-size: 13px; flex: 1; }
  .check-sub { font-size: 11px; color: var(--muted); margin-top: 2px; }

  /* ── AI output / typewriter ── */
  .ai-output {
    background: var(--surface); border: 1px solid var(--border); border-radius: 8px;
    padding: 20px; font-family: var(--font-mono); font-size: 12.5px; line-height: 1.7;
    color: var(--dim); white-space: pre-wrap; max-height: 480px; overflow-y: auto;
  }
  .ai-output .cursor { display: inline-block; width: 2px; height: 14px; background: var(--blue); animation: blink .7s infinite; vertical-align: middle; margin-left: 2px; }
  @keyframes blink { 0%,100%{opacity:1} 50%{opacity:0} }

  /* ── Profile / Cover letter output ── */
  .doc-output {
    background: #fff; color: #1a1a1a; border-radius: 8px; padding: 40px 48px;
    font-family: 'Inter', sans-serif; font-size: 14px; line-height: 1.7; max-width: 760px;
    box-shadow: 0 8px 40px rgba(0,0,0,.4);
  }
  .doc-output h1 { font-family: var(--font-display); font-size: 24px; font-weight: 700; color: #0A0F1E; margin-bottom: 2px; }
  .doc-output h2 { font-size: 13px; font-weight: 600; text-transform: uppercase; letter-spacing: 2px; color: #3B82F6; border-bottom: 2px solid #3B82F6; padding-bottom: 4px; margin: 20px 0 10px; }
  .doc-output h3 { font-size: 14px; font-weight: 600; color: #1a1a1a; margin-bottom: 2px; }
  .doc-output p { margin-bottom: 10px; color: #374151; }
  .doc-output ul { padding-left: 18px; margin-bottom: 10px; }
  .doc-output li { margin-bottom: 5px; color: #374151; }
  .doc-contact { font-size: 13px; color: #64748B; margin-bottom: 16px; }
  .doc-job-meta { font-size: 12px; color: #64748B; }

  /* ── Progress bar ── */
  .progress-bar-bg { background: var(--border); border-radius: 4px; height: 6px; overflow: hidden; margin-top: 4px; }
  .progress-bar-fill { height: 100%; border-radius: 4px; transition: width 1s ease; }

  /* ── Tabs ── */
  .tabs { display: flex; gap: 4px; border-bottom: 1px solid var(--border); margin-bottom: 24px; }
  .tab {
    padding: 10px 18px; font-size: 13px; font-weight: 500; cursor: pointer;
    border-bottom: 2px solid transparent; color: var(--muted); transition: all .15s; margin-bottom: -1px;
  }
  .tab:hover { color: var(--text); }
  .tab.active { color: var(--blue); border-bottom-color: var(--blue); }

  /* ── Loading spinner ── */
  .spinner {
    width: 20px; height: 20px; border: 2px solid var(--border);
    border-top-color: var(--blue); border-radius: 50%; animation: spin .6s linear infinite;
  }
  @keyframes spin { to { transform: rotate(360deg); } }

  /* ── Misc ── */
  .empty-state { text-align: center; padding: 60px 20px; color: var(--muted); }
  .empty-state .icon { font-size: 48px; margin-bottom: 12px; }
  .empty-state p { font-size: 14px; }
  .grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
  .grid-3 { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 16px; }
  .stat-card { background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 18px; }
  .stat-value { font-family: var(--font-display); font-size: 28px; font-weight: 700; }
  .stat-label { font-size: 12px; color: var(--muted); margin-top: 4px; }
  .tag { display: inline-block; padding: 3px 9px; border-radius: 4px; font-size: 11px; font-weight: 600; letter-spacing: .5px; }
  .tag-blue { background: var(--blue-dim); color: var(--blue); }
  .tag-green { background: rgba(16,185,129,.15); color: var(--green); }
  .tag-gold { background: rgba(245,158,11,.15); color: var(--gold); }
  .tag-red { background: rgba(239,68,68,.15); color: var(--red); }
  .divider { height: 1px; background: var(--border); margin: 20px 0; }
  .text-muted { color: var(--muted); font-size: 13px; }
  .text-mono { font-family: var(--font-mono); font-size: 12px; }
  .flex { display: flex; } .gap-8 { gap: 8px; } .gap-12 { gap: 12px; } .gap-16 { gap: 16px; }
  .align-center { align-items: center; } .justify-between { justify-content: space-between; }
  .w-full { width: 100%; } .mb-16 { margin-bottom: 16px; } .mb-8 { margin-bottom: 8px; }
  .mt-16 { margin-top: 16px; } .mt-8 { margin-top: 8px; }
  textarea { font-family: var(--font-body); }

  /* Notification toast */
  .toast {
    position: fixed; bottom: 24px; right: 24px; background: var(--panel); border: 1px solid var(--green);
    color: var(--text); padding: 12px 18px; border-radius: 8px; font-size: 13px;
    box-shadow: 0 8px 24px rgba(0,0,0,.4); z-index: 999; animation: slideUp .3s ease;
    display: flex; align-items: center; gap: 10px;
  }
  @keyframes slideUp { from{transform:translateY(20px);opacity:0} to{transform:translateY(0);opacity:1} }

  /* Scrollbar */
  ::-webkit-scrollbar { width: 6px; height: 6px; }
  ::-webkit-scrollbar-track { background: var(--surface); }
  ::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }
  ::-webkit-scrollbar-thumb:hover { background: var(--muted); }
`;

// ─── Mock AI calls ────────────────────────────────────────────────────────────
async function callClaude(systemPrompt, userPrompt, onStream) {
  try {
    const response = await fetch("https://api.anthropic.com/v1/messages", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        model: "claude-sonnet-4-20250514",
        max_tokens: 1000,
        system: systemPrompt,
        messages: [{ role: "user", content: userPrompt }],
      }),
    });
    const data = await response.json();
    const text = data.content?.map(b => b.text || "").join("") || "";
    // simulate streaming
    for (let i = 0; i < text.length; i += 8) {
      await new Promise(r => setTimeout(r, 12));
      onStream(text.slice(0, i + 8));
    }
    onStream(text);
    return text;
  } catch (e) {
    const err = "⚠️ API error: " + e.message;
    onStream(err);
    return err;
  }
}

// ─── Sample parsed resume ─────────────────────────────────────────────────────
const SAMPLE_RESUME = {
  name: "Priya Sharma",
  title: "Senior Software Engineer",
  contact: { email: "priya.sharma@email.com", phone: "+64 21 555 0192", location: "Auckland, NZ", linkedin: "linkedin.com/in/priyasharma" },
  summary: "Full-stack engineer with 6+ years building scalable web applications. Strong in React, Node.js, and cloud infrastructure. Passionate about AI/ML integration.",
  experience: [
    { title: "Senior Software Engineer", company: "Xero", period: "2021–Present", bullets: ["Led migration of legacy APIs to microservices (AWS)", "Built React component library used by 12 teams", "Mentored 3 junior engineers"] },
    { title: "Software Engineer", company: "Trade Me", period: "2018–2021", bullets: ["Full-stack development with React and .NET Core", "Reduced page load time 40% via caching strategy", "Implemented A/B testing framework"] },
    { title: "Junior Developer", company: "Catalyst IT", period: "2016–2018", bullets: ["Ruby on Rails web apps", "REST API design and integration"] },
  ],
  skills: { technical: ["React","TypeScript","Node.js","Python","AWS","Docker","PostgreSQL","GraphQL","CI/CD","Terraform"], soft: ["Team leadership","Agile/Scrum","Mentoring","Technical writing"] },
  education: [{ degree: "B.Sc. Computer Science", institution: "University of Auckland", year: "2016" }],
  certifications: ["AWS Solutions Architect Associate (2022)"],
};

// ─── Colour helpers ───────────────────────────────────────────────────────────
function scoreColor(s) {
  if (s >= 75) return "var(--green)";
  if (s >= 50) return "var(--gold)";
  return "var(--red)";
}
function scoreClass(s) {
  if (!s) return "score-none";
  if (s >= 75) return "score-high";
  if (s >= 50) return "score-med";
  return "score-low";
}

// ─── ScoreRing ────────────────────────────────────────────────────────────────
function ScoreRing({ score, loading }) {
  const r = 68, c = 2 * Math.PI * r;
  const fill = loading ? 0 : (score / 100) * c;
  const color = scoreColor(score);
  return (
    <div className="score-ring">
      <svg viewBox="0 0 160 160" width="160" height="160">
        <circle cx="80" cy="80" r={r} fill="none" stroke="var(--border)" strokeWidth="8" />
        <circle cx="80" cy="80" r={r} fill="none" stroke={color} strokeWidth="8"
          strokeDasharray={c} strokeDashoffset={c - fill}
          strokeLinecap="round" style={{ transition: "stroke-dashoffset 1.2s ease" }} />
      </svg>
      <div style={{ textAlign: "center" }}>
        {loading
          ? <div className="spinner" style={{ margin: "0 auto" }} />
          : <div className="score-ring-num" style={{ color }}>{score}</div>
        }
        <div className="score-ring-label">MATCH SCORE</div>
      </div>
    </div>
  );
}

// ─── Main App ─────────────────────────────────────────────────────────────────
export default function CareerAgent() {
  const [page, setPage] = useState("dashboard");
  const [resume, setResume] = useState(null);
  const [resumeRaw, setResumeRaw] = useState("");
  const [jobs, setJobs] = useState([]);
  const [jobInput, setJobInput] = useState("");
  const [selectedJob, setSelectedJob] = useState(null);
  const [evaluations, setEvaluations] = useState({});
  const [profiles, setProfiles] = useState({});
  const [toast, setToast] = useState(null);
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [evalLoading, setEvalLoading] = useState(false);
  const [profileLoading, setProfileLoading] = useState(false);
  const [evalStream, setEvalStream] = useState("");
  const [profileStream, setProfileStream] = useState("");
  const [coverStream, setCoverStream] = useState("");
  const [profileTab, setProfileTab] = useState("profile");
  const [missingChecked, setMissingChecked] = useState({});
  const fileRef = useRef();

  function showToast(msg, color = "var(--green)") {
    setToast({ msg, color });
    setTimeout(() => setToast(null), 3000);
  }

  // ── Upload / parse resume ──────────────────────────────────────────────────
  async function handleResumeFile(file) {
    if (!file) return;
    setUploading(true);
    await new Promise(r => setTimeout(r, 1800)); // simulate parsing
    setResume(SAMPLE_RESUME);
    setResumeRaw(file.name);
    setUploading(false);
    showToast("✓ Resume parsed and indexed into your personal knowledge base");
    setPage("resume");
  }

  // ── Add job ────────────────────────────────────────────────────────────────
  function addJob() {
    const text = jobInput.trim();
    if (!text) return;
    const lines = text.split("\n").filter(Boolean);
    const title = lines[0] || "Untitled Role";
    const company = lines[1] || "Company";
    const newJob = { id: Date.now(), title, company, raw: text, addedAt: new Date().toLocaleDateString("en-NZ") };
    setJobs(j => [newJob, ...j]);
    setJobInput("");
    showToast("✓ Job saved to your pipeline");
  }

  // ── Evaluate ───────────────────────────────────────────────────────────────
  async function evaluate(job) {
    if (!resume) return showToast("⚠️ Please upload your resume first", "var(--gold)");
    setSelectedJob(job);
    setPage("evaluate");
    setEvalLoading(true);
    setEvalStream("");
    setMissingChecked({});

    const sys = `You are an expert NZ career coach and recruiter. Analyse fit between resume and job. 
Respond in this EXACT JSON format (no markdown, no backticks):
{
  "score": <0-100>,
  "verdict": "<one sentence>",
  "strengths": ["<item>","<item>","<item>"],
  "gaps": ["<item>","<item>"],
  "missing_skills": [{"skill":"<name>","importance":"high|medium","question":"<Yes/No question to ask candidate>"}],
  "recommendations": ["<item>","<item>"]
}`;
    const usr = `RESUME:\n${JSON.stringify(resume)}\n\nJOB POSTING:\n${job.raw}`;

    let fullText = "";
    await callClaude(sys, usr, t => { fullText = t; setEvalStream(t); });
    setEvalLoading(false);

    try {
      const clean = fullText.replace(/```json|```/g, "").trim();
      const parsed = JSON.parse(clean);
      setEvaluations(e => ({ ...e, [job.id]: parsed }));
      setJobs(j => j.map(jj => jj.id === job.id ? { ...jj, score: parsed.score } : jj));
    } catch { /* keep raw stream */ }
  }

  // ── Generate profile ───────────────────────────────────────────────────────
  async function generateProfile(job) {
    if (!resume) return;
    const ev = evaluations[job.id];
    setProfileLoading(true);
    setProfileStream("");
    setCoverStream("");
    setPage("profile");

    const confirmedSkills = Object.entries(missingChecked)
      .filter(([, v]) => v).map(([k]) => k).join(", ");

    const sys = `You are an expert NZ career coach. Generate a tailored CV profile summary and cover letter in NZ professional format.
Return EXACTLY this JSON (no markdown):
{
  "profile_summary": "<3-4 sentences tailored profile summary>",
  "key_achievements": ["<achievement>","<achievement>","<achievement>"],
  "cover_letter": "<full NZ-format cover letter, formal, 4 paragraphs, signed off with Yours sincerely>"
}`;
    const usr = `Resume: ${JSON.stringify(resume)}\nJob: ${job.raw}\nAdditional skills confirmed by candidate: ${confirmedSkills || "none"}\nMatch score: ${ev?.score || "N/A"}\nStrengths: ${ev?.strengths?.join(", ") || ""}`;

    let fullText = "";
    await callClaude(sys, usr, t => { fullText = t; setProfileStream(t); });
    setProfileLoading(false);

    try {
      const clean = fullText.replace(/```json|```/g, "").trim();
      const parsed = JSON.parse(clean);
      setProfiles(p => ({ ...p, [job.id]: parsed }));
    } catch { }
  }

  // ── Render helpers ─────────────────────────────────────────────────────────
  const ev = selectedJob ? evaluations[selectedJob.id] : null;
  const prof = selectedJob ? profiles[selectedJob.id] : null;

  // ════════════════════════════════════════════════════════════════════════════
  return (
    <>
      <style>{styles}</style>
      <div className="app">
        {/* ── Sidebar ── */}
        <aside className="sidebar">
          <div className="sidebar-logo">
            Career<span>AI</span>
            <small>Personal Agent</small>
          </div>
          <div className="nav-section">Workspace</div>
          {[
            { id:"dashboard", icon:"⊞", label:"Dashboard" },
            { id:"resume",    icon:"📄", label:"My Resume", badge: resume ? "✓" : null },
            { id:"jobs",      icon:"💼", label:"Job Pipeline", badge: jobs.length || null },
            { id:"evaluate",  icon:"⚡", label:"Evaluate", badge: selectedJob ? "1" : null },
            { id:"profile",   icon:"✨", label:"Generated Docs", badge: prof ? "Ready" : null },
          ].map(n => (
            <div key={n.id} className={`nav-item ${page===n.id?"active":""}`} onClick={() => setPage(n.id)}>
              <span className="icon">{n.icon}</span>
              {n.label}
              {n.badge && <span className="nav-badge">{n.badge}</span>}
            </div>
          ))}
          <div className="nav-section">Tools</div>
          <div className="nav-item"><span className="icon">🔍</span>Job Scout</div>
          <div className="nav-item"><span className="icon">📊</span>Market Intel</div>
          <div className="sidebar-footer">
            <span className="status-dot" />
            <span style={{ fontSize: 12, color: "var(--dim)" }}>AI Agent active</span>
          </div>
        </aside>

        {/* ── Main Content ── */}
        <main className="main">

          {/* ──────── DASHBOARD ──────── */}
          {page === "dashboard" && (
            <>
              <div className="topbar">
                <div>
                  <div className="page-title">Good morning, <span>Sharma</span> 👋</div>
                  <div className="text-muted mt-8">Your career intelligence centre</div>
                </div>
                <div className="topbar-actions">
                  <button className="btn btn-primary" onClick={() => setPage("jobs")}>+ Add Job</button>
                </div>
              </div>
              <div className="grid-3 mb-16">
                <div className="stat-card">
                  <div className="stat-value" style={{ color:"var(--blue)" }}>{jobs.length}</div>
                  <div className="stat-label">Jobs in Pipeline</div>
                </div>
                <div className="stat-card">
                  <div className="stat-value" style={{ color:"var(--gold)" }}>{Object.keys(evaluations).length}</div>
                  <div className="stat-label">Roles Evaluated</div>
                </div>
                <div className="stat-card">
                  <div className="stat-value" style={{ color:"var(--green)" }}>{Object.keys(profiles).length}</div>
                  <div className="stat-label">Profiles Generated</div>
                </div>
              </div>
              {!resume ? (
                <div className="card">
                  <div className="card-header">
                    <div><div className="card-title">🚀 Get Started</div><div className="card-sub">Upload your resume to begin</div></div>
                  </div>
                  <div
                    className={`upload-zone ${dragging ? "drag" : ""}`}
                    onDragOver={e => { e.preventDefault(); setDragging(true); }}
                    onDragLeave={() => setDragging(false)}
                    onDrop={e => { e.preventDefault(); setDragging(false); handleResumeFile(e.dataTransfer.files[0]); }}
                    onClick={() => fileRef.current?.click()}
                  >
                    <input ref={fileRef} type="file" accept=".pdf,.doc,.docx,.txt" onChange={e => handleResumeFile(e.target.files[0])} />
                    <div className="upload-icon">{uploading ? "⏳" : "📤"}</div>
                    <h3>{uploading ? "Parsing your resume…" : "Drop your resume here"}</h3>
                    <p>{uploading ? "Extracting skills, experience & education…" : "PDF, DOCX, or TXT · Your data stays private"}</p>
                  </div>
                </div>
              ) : (
                <div className="grid-2">
                  <div className="card">
                    <div className="card-header">
                      <div><div className="card-title">📄 Resume Status</div><div className="card-sub">{resume.name} · {resume.title}</div></div>
                      <span className="tag tag-green">Indexed</span>
                    </div>
                    <p className="text-muted">{resume.experience.length} roles · {resume.skills.technical.length} technical skills · {resume.education.length} qualifications</p>
                    <div className="divider" />
                    <button className="btn btn-secondary btn-sm" onClick={() => setPage("resume")}>View details →</button>
                  </div>
                  <div className="card">
                    <div className="card-header">
                      <div><div className="card-title">💼 Top Match</div><div className="card-sub">Highest scoring role</div></div>
                    </div>
                    {jobs.filter(j => j.score).sort((a,b) => b.score - a.score)[0] ? (() => {
                      const top = jobs.filter(j => j.score).sort((a,b) => b.score - a.score)[0];
                      return (<>
                        <div className="flex align-center gap-12">
                          <div className={`job-score-badge ${scoreClass(top.score)}`}>{top.score}</div>
                          <div><div className="job-title">{top.title}</div><div className="job-company">{top.company}</div></div>
                        </div>
                        <div className="divider" />
                        <button className="btn btn-primary btn-sm" onClick={() => { setSelectedJob(top); setPage("evaluate"); }}>View evaluation →</button>
                      </>);
                    })() : <div className="text-muted">Evaluate a job to see your top match</div>}
                  </div>
                </div>
              )}
            </>
          )}

          {/* ──────── RESUME ──────── */}
          {page === "resume" && (
            <>
              <div className="topbar">
                <div className="page-title">My <span>Resume</span></div>
                <div className="topbar-actions">
                  <button className="btn btn-secondary" onClick={() => fileRef.current?.click()}>↑ Re-upload</button>
                  <input ref={fileRef} type="file" style={{ display:"none" }} onChange={e => handleResumeFile(e.target.files[0])} />
                </div>
              </div>
              {!resume ? (
                <div className="card">
                  <div
                    className={`upload-zone ${dragging ? "drag" : ""}`}
                    onDragOver={e => { e.preventDefault(); setDragging(true); }}
                    onDragLeave={() => setDragging(false)}
                    onDrop={e => { e.preventDefault(); setDragging(false); handleResumeFile(e.dataTransfer.files[0]); }}
                    onClick={() => fileRef.current?.click()}
                  >
                    <div className="upload-icon">📤</div>
                    <h3>Upload your resume</h3>
                    <p>PDF, DOCX, or TXT — we'll parse and index everything</p>
                  </div>
                </div>
              ) : (
                <>
                  <div className="card mb-16">
                    <div className="flex align-center gap-16">
                      <div style={{ width:56, height:56, borderRadius:"50%", background:"var(--blue-dim)", display:"flex", alignItems:"center", justifyContent:"center", fontSize:22, flexShrink:0 }}>👩‍💻</div>
                      <div>
                        <div style={{ fontFamily:"var(--font-display)", fontWeight:700, fontSize:20 }}>{resume.name}</div>
                        <div style={{ color:"var(--blue)", fontWeight:600, fontSize:14 }}>{resume.title}</div>
                        <div className="text-muted mt-8">{Object.values(resume.contact).join(" · ")}</div>
                      </div>
                      <span className="tag tag-green" style={{ marginLeft:"auto" }}>✓ Indexed</span>
                    </div>
                    <div className="divider" />
                    <p style={{ fontSize:13, lineHeight:1.7, color:"var(--dim)" }}>{resume.summary}</p>
                  </div>
                  <div className="resume-grid">
                    <div style={{ display:"flex", flexDirection:"column", gap:16 }}>
                      <div className="resume-section">
                        <h4>Technical Skills</h4>
                        {resume.skills.technical.map(s => <span key={s} className="skill-chip">{s}</span>)}
                      </div>
                      <div className="resume-section">
                        <h4>Soft Skills</h4>
                        {resume.skills.soft.map(s => <span key={s} className="skill-chip soft">{s}</span>)}
                      </div>
                      <div className="resume-section">
                        <h4>Education & Certs</h4>
                        {resume.education.map(e => (
                          <div key={e.degree} className="exp-item">
                            <div className="exp-title">{e.degree}</div>
                            <div className="exp-meta">{e.institution} · {e.year}</div>
                          </div>
                        ))}
                        {resume.certifications.map(c => (
                          <div key={c} className="flex align-center gap-8" style={{ marginTop:8 }}>
                            <span className="tag tag-gold">CERT</span>
                            <span style={{ fontSize:13 }}>{c}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                    <div className="resume-section">
                      <h4>Work Experience</h4>
                      {resume.experience.map(e => (
                        <div key={e.company} className="exp-item">
                          <div className="exp-title">{e.title}</div>
                          <div className="exp-meta">{e.company} · {e.period}</div>
                          <ul style={{ paddingLeft:16, marginTop:8 }}>
                            {e.bullets.map(b => <li key={b} style={{ fontSize:12, color:"var(--dim)", marginBottom:4 }}>{b}</li>)}
                          </ul>
                        </div>
                      ))}
                    </div>
                  </div>
                </>
              )}
            </>
          )}

          {/* ──────── JOBS ──────── */}
          {page === "jobs" && (
            <>
              <div className="topbar">
                <div className="page-title">Job <span>Pipeline</span></div>
                <span className="tag tag-blue">{jobs.length} saved</span>
              </div>
              <div className="card mb-16">
                <div className="card-title mb-8">Paste a Job Posting</div>
                <div className="text-muted mb-16" style={{ fontSize:12 }}>Copy the full job description from any job board (Seek, LinkedIn, Trade Me Jobs…)</div>
                <textarea
                  className="job-input-area w-full"
                  placeholder={"Senior Software Engineer — Xero\nAuckland, NZ · Full time\n\nWe're looking for a senior engineer to join our Platform team…\n\n[Paste full job description here]"}
                  value={jobInput}
                  onChange={e => setJobInput(e.target.value)}
                />
                <div className="flex gap-8 mt-16">
                  <button className="btn btn-primary" onClick={addJob} disabled={!jobInput.trim()}>+ Save Job</button>
                  <button className="btn btn-secondary" onClick={() => setJobInput("")}>Clear</button>
                </div>
              </div>
              {jobs.length === 0
                ? <div className="empty-state"><div className="icon">💼</div><p>No jobs saved yet. Paste a job posting above.</p></div>
                : (
                  <div className="job-list">
                    {jobs.map(job => (
                      <div key={job.id} className={`job-card ${selectedJob?.id===job.id?"selected":""}`} onClick={() => { setSelectedJob(job); }}>
                        <div className={`job-score-badge ${scoreClass(job.score)}`}>{job.score || "—"}</div>
                        <div className="job-card-body">
                          <div className="job-title">{job.title}</div>
                          <div className="job-company">{job.company} · Added {job.addedAt}</div>
                          <div className="job-snippet">{job.raw}</div>
                        </div>
                        <div className="flex gap-8" style={{ flexShrink:0 }}>
                          <button className="btn btn-secondary btn-sm" onClick={e => { e.stopPropagation(); evaluate(job); }}>
                            ⚡ Evaluate
                          </button>
                          {evaluations[job.id] && (
                            <button className="btn btn-gold btn-sm" onClick={e => { e.stopPropagation(); setSelectedJob(job); generateProfile(job); }}>
                              ✨ Generate
                            </button>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )
              }
            </>
          )}

          {/* ──────── EVALUATE ──────── */}
          {page === "evaluate" && (
            <>
              <div className="topbar">
                <div>
                  <div className="page-title">Job <span>Evaluation</span></div>
                  {selectedJob && <div className="text-muted mt-8">{selectedJob.title} · {selectedJob.company}</div>}
                </div>
                <div className="topbar-actions">
                  {!selectedJob
                    ? <button className="btn btn-primary" onClick={() => setPage("jobs")}>Pick a Job →</button>
                    : <button className="btn btn-secondary" onClick={() => { evaluate(selectedJob); }}>⟳ Re-evaluate</button>
                  }
                </div>
              </div>
              {!selectedJob
                ? <div className="empty-state"><div className="icon">⚡</div><p>Select a job from the pipeline to evaluate it against your resume.</p><div className="mt-16"><button className="btn btn-primary" onClick={() => setPage("jobs")}>Go to Pipeline →</button></div></div>
                : !resume
                ? <div className="empty-state"><div className="icon">📄</div><p>Please upload your resume first.</p><div className="mt-16"><button className="btn btn-primary" onClick={() => setPage("resume")}>Upload Resume →</button></div></div>
                : (
                  <>
                    {(evalLoading || !ev) ? (
                      <div className="card">
                        <div style={{ textAlign:"center", padding:"40px 0" }}>
                          <ScoreRing score={0} loading={true} />
                          <div className="text-muted mt-16">Analysing your resume against this role…</div>
                          <div className="ai-output mt-16" style={{ textAlign:"left", maxHeight:200 }}>
                            {evalStream}<span className="cursor" />
                          </div>
                        </div>
                      </div>
                    ) : (
                      <div className="eval-grid">
                        {/* Left: Score + summary */}
                        <div style={{ display:"flex", flexDirection:"column", gap:16 }}>
                          <div className="card" style={{ textAlign:"center" }}>
                            <ScoreRing score={ev.score} />
                            <div className="divider" />
                            <div style={{ fontSize:13, color:"var(--dim)", lineHeight:1.6 }}>{ev.verdict}</div>
                            <div className="divider" />
                            <div className="progress-bar-bg mb-8">
                              <div className="progress-bar-fill" style={{ width:`${ev.score}%`, background: scoreColor(ev.score) }} />
                            </div>
                            <div style={{ display:"flex", justifyContent:"space-between", fontSize:11, color:"var(--muted)" }}>
                              <span>Poor fit</span><span>Strong fit</span>
                            </div>
                          </div>
                          {ev.score >= 50 && (
                            <button className="btn btn-gold btn-lg w-full" onClick={() => generateProfile(selectedJob)}>
                              ✨ Generate Tailored Profile
                            </button>
                          )}
                        </div>

                        {/* Right: Details */}
                        <div className="card">
                          <div className="eval-section">
                            <h4>Strengths</h4>
                            {ev.strengths?.map(s => (
                              <div key={s} className="eval-item">
                                <div className="eval-dot" style={{ background:"var(--green)" }} />
                                <span style={{ fontSize:13 }}>{s}</span>
                              </div>
                            ))}
                          </div>
                          <div className="eval-section">
                            <h4>Gaps</h4>
                            {ev.gaps?.map(g => (
                              <div key={g} className="eval-item">
                                <div className="eval-dot" style={{ background:"var(--red)" }} />
                                <span style={{ fontSize:13 }}>{g}</span>
                              </div>
                            ))}
                          </div>
                          <div className="eval-section">
                            <h4>Do you have these skills? (not listed on resume)</h4>
                            {ev.missing_skills?.map(m => (
                              <div
                                key={m.skill}
                                className={`missing-check ${missingChecked[m.skill] ? "checked" : ""}`}
                                onClick={() => setMissingChecked(c => ({ ...c, [m.skill]: !c[m.skill] }))}
                              >
                                <div className="check-box">{missingChecked[m.skill] ? "✓" : ""}</div>
                                <div>
                                  <div className="check-label">{m.question}</div>
                                  <div className="check-sub">
                                    <span className={`tag tag-${m.importance === "high" ? "red" : "gold"}`} style={{ marginRight:6 }}>{m.importance}</span>
                                    {m.skill}
                                  </div>
                                </div>
                              </div>
                            ))}
                          </div>
                          {ev.recommendations?.length > 0 && (
                            <div className="eval-section">
                              <h4>Recommendations</h4>
                              {ev.recommendations.map(r => (
                                <div key={r} className="eval-item">
                                  <div className="eval-dot" style={{ background:"var(--blue)" }} />
                                  <span style={{ fontSize:13 }}>{r}</span>
                                </div>
                              ))}
                            </div>
                          )}
                          <div className="divider" />
                          <button className="btn btn-gold" onClick={() => generateProfile(selectedJob)}>
                            ✨ Generate Profile + Cover Letter
                          </button>
                        </div>
                      </div>
                    )}
                  </>
                )
              }
            </>
          )}

          {/* ──────── PROFILE / COVER LETTER ──────── */}
          {page === "profile" && (
            <>
              <div className="topbar">
                <div>
                  <div className="page-title">Generated <span>Documents</span></div>
                  {selectedJob && <div className="text-muted mt-8">{selectedJob.title} · {selectedJob.company}</div>}
                </div>
                <div className="topbar-actions">
                  {prof && <button className="btn btn-secondary" onClick={() => { navigator.clipboard.writeText(profileTab === "profile" ? prof.cover_letter : prof.profile_summary); showToast("Copied to clipboard ✓"); }}>⎘ Copy</button>}
                </div>
              </div>

              {!selectedJob
                ? <div className="empty-state"><div className="icon">✨</div><p>Evaluate a job first, then generate your tailored profile.</p></div>
                : profileLoading || !prof
                ? (
                  <div className="card">
                    <div style={{ textAlign:"center", padding:"20px 0 10px" }}>
                      <div className="spinner" style={{ margin:"0 auto 16px" }} />
                      <div className="text-muted mb-16">Crafting your tailored profile and NZ cover letter…</div>
                    </div>
                    <div className="ai-output">{profileStream || coverStream}<span className="cursor" /></div>
                  </div>
                )
                : (
                  <>
                    <div className="tabs">
                      {[["profile","👤 Profile Summary"],["cover","📝 Cover Letter"]].map(([id, label]) => (
                        <div key={id} className={`tab ${profileTab===id?"active":""}`} onClick={() => setProfileTab(id)}>{label}</div>
                      ))}
                    </div>

                    {profileTab === "profile" && (
                      <div className="doc-output">
                        <h1>{resume?.name || "Your Name"}</h1>
                        <div className="doc-contact">{Object.values(resume?.contact || {}).join(" · ")}</div>
                        <h2>Profile Summary</h2>
                        <p>{prof.profile_summary}</p>
                        <h2>Key Achievements</h2>
                        <ul>{prof.key_achievements?.map(a => <li key={a}>{a}</li>)}</ul>
                        <h2>Technical Skills</h2>
                        <p>{resume?.skills?.technical?.join(", ")}</p>
                        <h2>Experience</h2>
                        {resume?.experience?.map(e => (
                          <div key={e.company} style={{ marginBottom:16 }}>
                            <h3>{e.title}</h3>
                            <div className="doc-job-meta">{e.company} · {e.period}</div>
                            <ul style={{ marginTop:8 }}>{e.bullets.map(b => <li key={b}>{b}</li>)}</ul>
                          </div>
                        ))}
                        <h2>Education</h2>
                        {resume?.education?.map(e => <p key={e.degree}><strong>{e.degree}</strong> — {e.institution}, {e.year}</p>)}
                      </div>
                    )}

                    {profileTab === "cover" && (
                      <div className="doc-output">
                        <div style={{ marginBottom:24 }}>
                          <p><strong>{resume?.name}</strong></p>
                          <p className="doc-contact">{resume?.contact?.email} · {resume?.contact?.phone}<br />{resume?.contact?.location}</p>
                          <p style={{ marginTop:12 }}>{new Date().toLocaleDateString("en-NZ", { year:"numeric", month:"long", day:"numeric" })}</p>
                        </div>
                        <div style={{ marginBottom:24 }}>
                          <p><strong>Hiring Manager</strong></p>
                          <p>{selectedJob?.company}</p>
                          <p>New Zealand</p>
                        </div>
                        <p><strong>Re: Application for {selectedJob?.title}</strong></p>
                        <div className="divider" />
                        <div style={{ whiteSpace:"pre-wrap", lineHeight:1.8 }}>{prof.cover_letter}</div>
                      </div>
                    )}
                  </>
                )
              }
            </>
          )}
        </main>

        {/* ── Toast ── */}
        {toast && (
          <div className="toast" style={{ borderColor: toast.color }}>
            <span>{toast.msg}</span>
          </div>
        )}
      </div>
    </>
  );
}
