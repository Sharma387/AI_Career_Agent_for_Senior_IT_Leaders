import { useState, useEffect, useCallback } from 'react';
import { useLocation, useNavigate, Link } from 'react-router-dom';
import { toast } from 'sonner';
import {
  ArrowLeft,
  ExternalLink,
  Zap,
  FileText,
  Mail,
  MessageSquare,
  Lightbulb,
  Download,
  RefreshCw,
  Edit3,
  Save,
  MapPin,
  Building2,
  Calendar,
  DollarSign,
  Award,
} from 'lucide-react';
import { api } from '../api/client';
import { useAuth } from '../context/AuthContext';
import { ScoreRing } from '../components/ScoreRing';
import type {
  JobPosting,
  MatchResult,
  MatchScoreBreakdown,
  ImprovementRecommendation,
  InterviewStrategy,
} from '../types';

interface SavedMatch {
  match_id: number;
  match_score: number;
  strengths: string[];
  gaps: string[];
  evidence: any[];
  explanation: string;
  recommendation: string;
  created_at: string;
  articulations: Array<{
    id: number;
    gap_text: string;
    has_skill: boolean;
    evidence: string;
  }>;
}

type TabId = 'match' | 'resume' | 'cover_letter' | 'interview' | 'tips';

function ScoreBar({ label, score, max, weight }: { label: string; score: number; max: number; weight: number }) {
  const pct = max > 0 ? (score / max) * 100 : 0;
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-sm">
        <span className="text-slate-400">{label}</span>
        <span className="font-medium text-slate-300 font-mono text-xs">{score}/{max} (×{weight})</span>
      </div>
      <div className="h-2 bg-[#1E2D4A] rounded-full overflow-hidden">
        <div className="h-full bg-blue-500 rounded-full transition-all duration-700" style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

export function JobDetail() {
  const location = useLocation();
  const navigate = useNavigate();
  const { profileId } = useAuth();

  const job: JobPosting | undefined = location.state?.job;

  const [activeTab, setActiveTab] = useState<TabId>('match');

  // Match state
  const [matchResult, setMatchResult] = useState<MatchResult | null>(null);
  const [matching, setMatching] = useState(false);
  const [matchLoaded, setMatchLoaded] = useState(false);
  const [currentMatchId, setCurrentMatchId] = useState<number | null>(null);
  const [skillArticulations, setSkillArticulations] = useState<Record<number, { hasSkill: boolean; evidence: string }>>({});

  // Materials state
  const [applicationId, setApplicationId] = useState<number | null>(null);
  const [generating, setGenerating] = useState(false);
  const [materialsReady, setMaterialsReady] = useState(false);
  const [editingMaterial, setEditingMaterial] = useState(false);
  const [editResume, setEditResume] = useState('');
  const [editCoverLetter, setEditCoverLetter] = useState('');
  const [saving, setSaving] = useState(false);
  const [regenerating, setRegenerating] = useState(false);

  // Interview state
  const [interviewStrategy, setInterviewStrategy] = useState<InterviewStrategy | null>(null);
  const [loadingStrategy, setLoadingStrategy] = useState(false);

  // Check for existing match on mount
  const loadExistingMatch = useCallback(async () => {
    if (!job || !profileId) return;
    try {
      const res = await api.match.getPrevious(job.id, profileId);
      if (res.data) {
        const saved: SavedMatch = res.data;
        setMatchResult({
          match_id: String(saved.match_id),
          match_score: saved.match_score,
          strengths: saved.strengths,
          gaps: saved.gaps,
          evidence: saved.evidence,
          explanation: saved.explanation,
          recommendation: saved.recommendation,
        });
        setCurrentMatchId(saved.match_id);
        const arts: Record<number, { hasSkill: boolean; evidence: string }> = {};
        saved.articulations.forEach((a) => {
          const idx = saved.gaps.findIndex((g) => g === a.gap_text);
          if (idx >= 0) {
            arts[idx] = { hasSkill: a.has_skill, evidence: a.evidence };
          }
        });
        setSkillArticulations(arts);
      }
    } catch {
      // No previous match
    } finally {
      setMatchLoaded(true);
    }
  }, [job, profileId]);

  useEffect(() => {
    loadExistingMatch();
  }, [loadExistingMatch]);

  // Check for existing application/materials
  useEffect(() => {
    if (!job || !profileId) return;
    api.applications.list(profileId).then((res) => {
      const app = res.data.find((a) => a.job.id === job.id);
      if (app) {
        setApplicationId(app.application_id);
        setMaterialsReady(true);
      }
    }).catch(() => null);
  }, [job, profileId]);

  if (!job) {
    return (
      <div className="flex flex-col items-center justify-center h-64 gap-4">
        <p className="text-slate-400">Job not found.</p>
        <Link to="/jobs" className="btn-primary text-sm">
          <ArrowLeft className="w-4 h-4 mr-2" /> Back to Jobs
        </Link>
      </div>
    );
  }

  const handleRunMatch = async () => {
    if (!profileId) return;
    setMatching(true);
    try {
      const res = await api.jobs.matchEnhanced(job.id, profileId);
      const data = res.data as any;
      setMatchResult(data);
      setCurrentMatchId(data.match_id ? Number(data.match_id) : null);
      toast.success('Match analysis complete!');
    } catch {
      toast.error('Failed to generate match analysis');
    } finally {
      setMatching(false);
    }
  };

  const handleGenerateMaterials = async () => {
    if (!profileId) return;
    setGenerating(true);
    try {
      const res = await api.jobs.generateMaterials(job.id, profileId);
      setApplicationId(res.data.application_id);
      setMaterialsReady(true);
      toast.success('Materials generated successfully!');
    } catch {
      toast.error('Failed to generate materials');
    } finally {
      setGenerating(false);
    }
  };

  const handleRegenerateMaterials = async () => {
    if (!profileId) return;
    setRegenerating(true);
    try {
      const res = await api.jobs.generateMaterials(job.id, profileId);
      setApplicationId(res.data.application_id);
      toast.success('Materials regenerated!');
    } catch {
      toast.error('Failed to regenerate materials');
    } finally {
      setRegenerating(false);
    }
  };

  const handleSaveMaterials = async () => {
    if (!applicationId) return;
    setSaving(true);
    try {
      await api.applications.updateMaterials(applicationId, editResume, editCoverLetter);
      setEditingMaterial(false);
      toast.success('Materials saved');
    } catch {
      toast.error('Failed to save materials');
    } finally {
      setSaving(false);
    }
  };

  const handleStartEdit = async () => {
    if (!applicationId) return;
    try {
      const res = await api.applications.getMaterials(applicationId);
      setEditResume(res.data.resume_version_text);
      setEditCoverLetter(res.data.cover_letter_text);
      setEditingMaterial(true);
    } catch {
      toast.error('Failed to load materials for editing');
    }
  };

  const handleGetStrategy = async () => {
    if (!profileId) return;
    setLoadingStrategy(true);
    try {
      const res = await api.jobs.getInterviewStrategy(job.id, profileId);
      setInterviewStrategy(res.data);
      toast.success('Interview strategy generated!');
    } catch {
      toast.error('Failed to generate interview strategy');
    } finally {
      setLoadingStrategy(false);
    }
  };

  const handleSaveArticulations = async () => {
    if (!currentMatchId || !matchResult) return;
    const arts = matchResult.gaps.map((gap, i) => ({
      gap_text: gap,
      has_skill: skillArticulations[i]?.hasSkill || false,
      evidence: skillArticulations[i]?.evidence || '',
    }));
    try {
      await api.match.saveArticulations(currentMatchId, arts);
      toast.success('Articulations saved!');

      // Check if any articulations confirm skills — if so, auto-regenerate match
      const confirmedSkills = arts.filter(a => a.has_skill && a.evidence.trim());
      if (confirmedSkills.length > 0 && profileId) {
        toast.info('Re-running match analysis with your new skill confirmations...');
        setMatching(true);
        try {
          const res = await api.jobs.matchEnhanced(job.id, profileId);
          const data = res.data as any;
          setMatchResult(data);
          setCurrentMatchId(data.match_id ? Number(data.match_id) : null);
          toast.success('Match analysis updated with your confirmed skills!');
        } catch {
          toast.error('Failed to regenerate match');
        } finally {
          setMatching(false);
        }
      }
    } catch {
      toast.error('Failed to save articulations');
    }
  };

  const breakdown: MatchScoreBreakdown | undefined = matchResult?.score_breakdown;
  const recommendations: ImprovementRecommendation[] = matchResult?.improvement_recommendations || [];

  const tabs: { id: TabId; label: string; icon: React.ReactNode }[] = [
    { id: 'match', label: 'Match Analysis', icon: <Zap className="w-3.5 h-3.5" /> },
    { id: 'resume', label: 'Resume', icon: <FileText className="w-3.5 h-3.5" /> },
    { id: 'cover_letter', label: 'Cover Letter', icon: <Mail className="w-3.5 h-3.5" /> },
    { id: 'interview', label: 'Interview Prep', icon: <MessageSquare className="w-3.5 h-3.5" /> },
    { id: 'tips', label: 'Interview Tips', icon: <Lightbulb className="w-3.5 h-3.5" /> },
  ];

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Back Navigation */}
      <button
        onClick={() => navigate('/jobs')}
        className="flex items-center gap-2 text-sm text-slate-400 hover:text-blue-400 transition-colors"
      >
        <ArrowLeft className="w-4 h-4" /> Back to Jobs
      </button>

      {/* Job Info Card */}
      <div className="card">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1 min-w-0">
            <h1 className="text-2xl font-bold text-white font-display truncate">{job.title}</h1>
            <p className="text-blue-400 font-semibold mt-1 flex items-center gap-2">
              <Building2 className="w-4 h-4" />
              {job.company}
            </p>

            <div className="flex flex-wrap items-center gap-2 mt-4">
              {job.location && (
                <span className="text-xs px-2.5 py-1 rounded-full bg-[#0E1628] border border-[#1E2D4A] text-slate-300 flex items-center gap-1.5">
                  <MapPin className="w-3 h-3" /> {job.location}
                </span>
              )}
              {job.seniority_level && (
                <span className="text-xs px-2.5 py-1 rounded-full bg-blue-500/10 border border-blue-500/20 text-blue-400 flex items-center gap-1.5">
                  <Award className="w-3 h-3" /> {job.seniority_level}
                </span>
              )}
              {job.salary_range && (
                <span className="text-xs px-2.5 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 flex items-center gap-1.5">
                  <DollarSign className="w-3 h-3" /> {job.salary_range}
                </span>
              )}
              <span className="text-[11px] px-2.5 py-1 rounded-full bg-[#0E1628] border border-[#1E2D4A] text-slate-500 font-mono">
                {job.source}
              </span>
              {job.created_at && (
                <span className="text-[11px] px-2.5 py-1 rounded-full bg-[#0E1628] border border-[#1E2D4A] text-slate-500 font-mono flex items-center gap-1.5">
                  <Calendar className="w-3 h-3" /> {new Date(job.created_at).toLocaleDateString()}
                </span>
              )}
            </div>
          </div>

          {job.url && (
            <a
              href={job.url}
              target="_blank"
              rel="noopener noreferrer"
              className="btn-primary text-xs shrink-0"
            >
              View Original Posting <ExternalLink className="w-3 h-3 ml-1.5" />
            </a>
          )}
        </div>

        {/* Job Description */}
        {job.description && (
          <div className="mt-6 pt-5 border-t border-[#1E2D4A]">
            <h3 className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-3">Job Description</h3>
            <div className="bg-[#0E1628] rounded-lg border border-[#1E2D4A] p-4 max-h-64 overflow-y-auto">
              <p className="text-sm text-slate-300 whitespace-pre-wrap leading-relaxed">{job.description}</p>
            </div>
          </div>
        )}
      </div>

      {/* Tabs */}
      <div className="border-b border-[#1E2D4A]">
        <div className="flex gap-1 overflow-x-auto">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors -mb-px flex items-center gap-2 whitespace-nowrap ${
                activeTab === tab.id
                  ? 'border-blue-500 text-blue-400'
                  : 'border-transparent text-slate-500 hover:text-slate-300'
              }`}
            >
              {tab.icon}
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Tab Content */}
      <div className="animate-fade-in">
        {activeTab === 'match' && (
          <MatchTab
            matchResult={matchResult}
            matching={matching}
            matchLoaded={matchLoaded}
            breakdown={breakdown}
            recommendations={recommendations}
            skillArticulations={skillArticulations}
            setSkillArticulations={setSkillArticulations}
            onRunMatch={handleRunMatch}
            onSaveArticulations={handleSaveArticulations}
          />
        )}

        {activeTab === 'resume' && (
          <MaterialsTab
            type="resume"
            applicationId={applicationId}
            materialsReady={materialsReady}
            generating={generating}
            regenerating={regenerating}
            editing={editingMaterial}
            editText={editResume}
            setEditText={setEditResume}
            saving={saving}
            onGenerate={handleGenerateMaterials}
            onRegenerate={handleRegenerateMaterials}
            onStartEdit={handleStartEdit}
            onSave={handleSaveMaterials}
            onCancelEdit={() => setEditingMaterial(false)}
          />
        )}

        {activeTab === 'cover_letter' && (
          <MaterialsTab
            type="cover_letter"
            applicationId={applicationId}
            materialsReady={materialsReady}
            generating={generating}
            regenerating={regenerating}
            editing={editingMaterial}
            editText={editCoverLetter}
            setEditText={setEditCoverLetter}
            saving={saving}
            onGenerate={handleGenerateMaterials}
            onRegenerate={handleRegenerateMaterials}
            onStartEdit={handleStartEdit}
            onSave={handleSaveMaterials}
            onCancelEdit={() => setEditingMaterial(false)}
          />
        )}

        {activeTab === 'interview' && (
          <InterviewTab
            strategy={interviewStrategy}
            loading={loadingStrategy}
            onGenerate={handleGetStrategy}
          />
        )}

        {activeTab === 'tips' && (
          <TipsTab seniorityLevel={job.seniority_level} title={job.title} />
        )}
      </div>
    </div>
  );
}

/* ─── Match Tab ─── */
function MatchTab({
  matchResult,
  matching,
  matchLoaded,
  breakdown,
  recommendations,
  skillArticulations,
  setSkillArticulations,
  onRunMatch,
  onSaveArticulations,
}: {
  matchResult: MatchResult | null;
  matching: boolean;
  matchLoaded: boolean;
  breakdown: MatchScoreBreakdown | undefined;
  recommendations: ImprovementRecommendation[];
  skillArticulations: Record<number, { hasSkill: boolean; evidence: string }>;
  setSkillArticulations: React.Dispatch<React.SetStateAction<Record<number, { hasSkill: boolean; evidence: string }>>>;
  onRunMatch: () => void;
  onSaveArticulations: () => void;
}) {
  if (!matchLoaded) {
    return (
      <div className="card flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500" />
      </div>
    );
  }

  if (!matchResult && !matching) {
    return (
      <div className="card text-center py-12">
        <Zap className="w-12 h-12 text-blue-500/30 mx-auto mb-4" />
        <h3 className="text-lg font-semibold text-white mb-2">Run Match Analysis</h3>
        <p className="text-sm text-slate-400 mb-6 max-w-md mx-auto">
          Compare your profile against this job posting to see your match score, strengths, gaps, and personalized recommendations.
        </p>
        <button onClick={onRunMatch} className="btn-primary">
          <Zap className="w-4 h-4 mr-2" /> Run Match
        </button>
      </div>
    );
  }

  if (matching) {
    return (
      <div className="card flex flex-col items-center justify-center py-12">
        <ScoreRing score={0} size={140} loading />
        <p className="text-sm text-slate-400 mt-4">Analyzing your profile against this position...</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Score + Summary */}
      <div className="card">
        <div className="flex flex-col md:flex-row items-center gap-8">
          <ScoreRing score={matchResult!.match_score} size={160} />
          <div className="flex-1">
            <p className="text-lg font-semibold text-white mb-2">{matchResult!.recommendation}</p>
            <p className="text-sm text-slate-400">{matchResult!.explanation}</p>
            <button onClick={onRunMatch} className="btn-ghost text-xs mt-4">
              <RefreshCw className="w-3 h-3 mr-1" /> Re-run Analysis
            </button>
          </div>
        </div>
      </div>

      {/* Score Breakdown */}
      {breakdown && (
        <div className="card">
          <h3 className="text-sm font-semibold text-white mb-4">Score Breakdown</h3>
          <div className="space-y-4">
            <ScoreBar label="Skills Match" score={breakdown.skills_match.score} max={breakdown.skills_match.max} weight={breakdown.skills_match.weight} />
            <ScoreBar label="Experience Match" score={breakdown.experience_match.score} max={breakdown.experience_match.max} weight={breakdown.experience_match.weight} />
            <ScoreBar label="Industry Relevance" score={breakdown.industry_relevance.score} max={breakdown.industry_relevance.max} weight={breakdown.industry_relevance.weight} />
            <ScoreBar label="Leadership Signals" score={breakdown.leadership_signals.score} max={breakdown.leadership_signals.max} weight={breakdown.leadership_signals.weight} />
          </div>
        </div>
      )}

      {/* Strengths & Gaps */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="card">
          <h3 className="text-xs font-medium text-emerald-400 uppercase tracking-wider mb-3">Strengths</h3>
          <ul className="space-y-2">
            {matchResult!.strengths.map((s, i) => (
              <li key={i} className="text-sm text-slate-300 flex items-start gap-2">
                <span className="w-2 h-2 rounded-full bg-emerald-400 mt-1.5 shrink-0" />
                {s}
              </li>
            ))}
          </ul>
        </div>
        <div className="card">
          <h3 className="text-xs font-medium text-amber-400 uppercase tracking-wider mb-3">Gaps</h3>
          <ul className="space-y-2">
            {matchResult!.gaps.map((g, i) => (
              <li key={i} className="text-sm text-slate-300 flex items-start gap-2">
                <span className="w-2 h-2 rounded-full bg-amber-400 mt-1.5 shrink-0" />
                {g}
              </li>
            ))}
          </ul>
        </div>
      </div>

      {/* Evidence */}
      {matchResult!.evidence.length > 0 && (
        <div className="card">
          <h3 className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-3">Evidence</h3>
          <ul className="space-y-2">
            {matchResult!.evidence.map((e, i) => {
              const text = typeof e === 'string' ? e : `${e.career_chunk} — ${e.relevance}`;
              return (
                <li key={i} className="text-sm text-slate-400 bg-[#0E1628] rounded-lg p-3 border border-[#1E2D4A]">
                  {text}
                </li>
              );
            })}
          </ul>
        </div>
      )}

      {/* Recommendations */}
      {recommendations.length > 0 && (
        <div className="card">
          <h3 className="text-sm font-semibold text-white mb-4">Improvement Recommendations</h3>
          <div className="space-y-3">
            {recommendations.map((rec, i) => (
              <div key={i} className="bg-[#0E1628] rounded-lg p-4 border border-[#1E2D4A]">
                <div className="flex items-center gap-2 mb-1">
                  <span className="font-medium text-sm text-slate-200">{rec.area}</span>
                  <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${
                    rec.priority === 'high' ? 'bg-red-500/10 text-red-400 border border-red-500/20' :
                    rec.priority === 'medium' ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20' :
                    'bg-slate-500/10 text-slate-400 border border-slate-500/20'
                  }`}>{rec.priority}</span>
                </div>
                <p className="text-xs text-slate-500 mb-1">Gap: {rec.gap}</p>
                <p className="text-sm text-slate-300">{rec.recommendation}</p>
                {rec.estimated_impact && (
                  <p className="text-xs text-emerald-400 mt-1.5">Impact: {rec.estimated_impact}</p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Skills Articulation */}
      {matchResult!.gaps.length > 0 && (
        <div className="card">
          <h3 className="text-sm font-semibold text-white mb-2">Skills Articulation</h3>
          <p className="text-xs text-slate-500 mb-4">
            Review the identified gaps. If you possess these skills, describe how you demonstrate them — this improves future match accuracy.
          </p>
          <div className="space-y-3">
            {matchResult!.gaps.map((gap, i) => (
              <div key={i} className={`bg-[#0E1628] rounded-lg p-4 border transition-colors ${skillArticulations[i]?.hasSkill ? 'border-emerald-500/30' : 'border-[#1E2D4A]'}`}>
                <p className="font-medium text-sm text-slate-200 mb-2">{gap}</p>
                <div className="flex items-center gap-4">
                  <label className="flex items-center gap-2 text-xs text-slate-400 cursor-pointer">
                    <input
                      type="radio"
                      name={`skill-${i}`}
                      checked={skillArticulations[i]?.hasSkill === true}
                      onChange={() => setSkillArticulations(prev => ({ ...prev, [i]: { hasSkill: true, evidence: prev[i]?.evidence || '' } }))}
                      className="text-blue-500"
                    />
                    I have this skill
                  </label>
                  <label className="flex items-center gap-2 text-xs text-slate-400 cursor-pointer">
                    <input
                      type="radio"
                      name={`skill-${i}`}
                      checked={skillArticulations[i]?.hasSkill === false}
                      onChange={() => setSkillArticulations(prev => ({ ...prev, [i]: { hasSkill: false, evidence: '' } }))}
                      className="text-blue-500"
                    />
                    Don't have this yet
                  </label>
                </div>
                {skillArticulations[i]?.hasSkill && (
                  <textarea
                    value={skillArticulations[i]?.evidence || ''}
                    onChange={(e) => setSkillArticulations(prev => ({ ...prev, [i]: { ...prev[i], evidence: e.target.value } }))}
                    className="input-field w-full mt-3"
                    rows={2}
                    placeholder="Describe how you demonstrate this skill..."
                  />
                )}
              </div>
            ))}
          </div>
          {Object.keys(skillArticulations).length > 0 && (
            <button onClick={onSaveArticulations} className="btn-primary mt-4">
              Save Articulations
            </button>
          )}
        </div>
      )}
    </div>
  );
}

/* ─── Materials Tab (Resume / Cover Letter) ─── */
function MaterialsTab({
  type,
  applicationId,
  materialsReady,
  generating,
  regenerating,
  editing,
  editText,
  setEditText,
  saving,
  onGenerate,
  onRegenerate,
  onStartEdit,
  onSave,
  onCancelEdit,
}: {
  type: 'resume' | 'cover_letter';
  applicationId: number | null;
  materialsReady: boolean;
  generating: boolean;
  regenerating: boolean;
  editing: boolean;
  editText: string;
  setEditText: (val: string) => void;
  saving: boolean;
  onGenerate: () => void;
  onRegenerate: () => void;
  onStartEdit: () => void;
  onSave: () => void;
  onCancelEdit: () => void;
}) {
  const isResume = type === 'resume';
  const label = isResume ? 'Resume' : 'Cover Letter';
  const Icon = isResume ? FileText : Mail;

  if (generating) {
    return (
      <div className="card flex flex-col items-center justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mb-3" />
        <p className="text-sm text-slate-400">Generating tailored materials...</p>
      </div>
    );
  }

  if (!materialsReady) {
    return (
      <div className="card text-center py-12">
        <Icon className="w-12 h-12 text-blue-500/30 mx-auto mb-4" />
        <h3 className="text-lg font-semibold text-white mb-2">Generate {label}</h3>
        <p className="text-sm text-slate-400 mb-6 max-w-md mx-auto">
          Create a tailored {label.toLowerCase()} optimized for this specific job posting using your profile data.
        </p>
        <button onClick={onGenerate} className="btn-primary">
          <FileText className="w-4 h-4 mr-2" /> Generate Materials
        </button>
      </div>
    );
  }

  return (
    <div className="card">
      {/* Toolbar */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-white flex items-center gap-2">
          <Icon className="w-4 h-4 text-blue-400" />
          {label}
        </h3>
        <div className="flex items-center gap-2">
          {!editing && (
            <>
              <button onClick={onRegenerate} disabled={regenerating} className="btn-gold text-xs">
                <RefreshCw className={`w-3 h-3 mr-1 ${regenerating ? 'animate-spin' : ''}`} />
                {regenerating ? 'Generating...' : 'Regenerate'}
              </button>
              <button onClick={onStartEdit} className="btn-ghost text-xs">
                <Edit3 className="w-3 h-3 mr-1" /> Edit
              </button>
            </>
          )}
        </div>
      </div>

      {/* Content */}
      {editing ? (
        <>
          <textarea
            value={editText}
            onChange={(e) => setEditText(e.target.value)}
            className="input-field w-full min-h-[350px] font-mono text-xs"
            rows={15}
          />
          <div className="flex justify-end gap-2 mt-4">
            <button onClick={onCancelEdit} className="btn-ghost text-xs">Cancel</button>
            <button onClick={onSave} disabled={saving} className="btn-primary text-xs">
              <Save className="w-3 h-3 mr-1" />
              {saving ? 'Saving...' : 'Save Changes'}
            </button>
          </div>
        </>
      ) : (
        <>
          <div className="bg-white rounded-lg border border-[#1E2D4A] overflow-hidden">
            {applicationId && (
              <iframe
                src={isResume
                  ? api.applications.previewResumeHtml(applicationId)
                  : api.applications.previewCoverLetterHtml(applicationId)
                }
                className="w-full min-h-[450px] border-0"
                title={`${label} Preview`}
              />
            )}
          </div>
          {applicationId && (
            <div className="flex gap-2 mt-4">
              <a
                href={isResume
                  ? api.applications.downloadResumeHtml(applicationId)
                  : api.applications.downloadCoverLetterHtml(applicationId)
                }
                download
                className="btn-ghost text-xs"
              >
                <Download className="w-3 h-3 mr-1" /> Download HTML
              </a>
              <a
                href={isResume
                  ? api.applications.downloadResumeDocx(applicationId)
                  : api.applications.downloadCoverLetterDocx(applicationId)
                }
                download
                className="btn-primary text-xs"
              >
                <Download className="w-3 h-3 mr-1" /> Download Word
              </a>
            </div>
          )}
        </>
      )}
    </div>
  );
}

/* ─── Interview Prep Tab ─── */
function InterviewTab({
  strategy,
  loading,
  onGenerate,
}: {
  strategy: InterviewStrategy | null;
  loading: boolean;
  onGenerate: () => void;
}) {
  if (loading) {
    return (
      <div className="card flex flex-col items-center justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-500 mb-3" />
        <p className="text-sm text-slate-400">Generating interview strategy...</p>
      </div>
    );
  }

  if (!strategy) {
    return (
      <div className="card text-center py-12">
        <MessageSquare className="w-12 h-12 text-purple-500/30 mx-auto mb-4" />
        <h3 className="text-lg font-semibold text-white mb-2">Interview Preparation</h3>
        <p className="text-sm text-slate-400 mb-6 max-w-md mx-auto">
          Generate a personalized interview strategy with key themes, potential questions, and talking points tailored to this role.
        </p>
        <button onClick={onGenerate} className="btn-primary">
          <MessageSquare className="w-4 h-4 mr-2" /> Generate Strategy
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Summary */}
      <div className="card">
        <div className="flex items-center gap-4 mb-4">
          <ScoreRing score={strategy.match_score} size={80} />
          <div>
            <p className="font-semibold text-white">{strategy.recommendation}</p>
            <p className="text-xs text-slate-400 mt-1">{strategy.explanation}</p>
          </div>
        </div>
        <button onClick={onGenerate} className="btn-ghost text-xs">
          <RefreshCw className="w-3 h-3 mr-1" /> Regenerate Strategy
        </button>
      </div>

      {/* Key Themes */}
      {strategy.key_themes.length > 0 && (
        <div className="card">
          <h3 className="text-xs font-medium text-purple-400 uppercase tracking-wider mb-3">Key Themes</h3>
          <div className="flex flex-wrap gap-2">
            {strategy.key_themes.map((theme, i) => (
              <span key={i} className="bg-purple-500/10 text-purple-400 border border-purple-500/20 px-3 py-1.5 rounded-full text-xs font-medium">
                {theme}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Potential Questions */}
      {strategy.potential_questions.length > 0 && (
        <div className="card">
          <h3 className="text-xs font-medium text-blue-400 uppercase tracking-wider mb-3">Potential Questions</h3>
          <ul className="space-y-2">
            {strategy.potential_questions.map((q, i) => (
              <li key={i} className="text-sm text-slate-300 bg-blue-500/5 border border-blue-500/10 rounded-lg p-3">
                {q}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Talking Points */}
      {strategy.talking_points.length > 0 && (
        <div className="card">
          <h3 className="text-xs font-medium text-emerald-400 uppercase tracking-wider mb-3">Talking Points</h3>
          <ul className="space-y-2">
            {strategy.talking_points.map((tp, i) => (
              <li key={i} className="text-sm text-slate-300 bg-emerald-500/5 border border-emerald-500/10 rounded-lg p-3">
                {tp}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Areas to Prepare */}
      {strategy.areas_to_prepare.length > 0 && (
        <div className="card">
          <h3 className="text-xs font-medium text-amber-400 uppercase tracking-wider mb-3">Areas to Prepare</h3>
          <ul className="space-y-2">
            {strategy.areas_to_prepare.map((a, i) => (
              <li key={i} className="text-sm text-slate-300 bg-amber-500/5 border border-amber-500/10 rounded-lg p-3">
                {a}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Strengths & Gaps */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="card">
          <h3 className="text-xs font-medium text-emerald-400 uppercase tracking-wider mb-3">Strengths to Highlight</h3>
          <ul className="space-y-1.5">
            {strategy.strengths.map((s, i) => (
              <li key={i} className="text-sm text-slate-300 flex items-start gap-2">
                <span className="w-2 h-2 rounded-full bg-emerald-400 mt-1.5 shrink-0" />
                {s}
              </li>
            ))}
          </ul>
        </div>
        <div className="card">
          <h3 className="text-xs font-medium text-amber-400 uppercase tracking-wider mb-3">Gaps to Address</h3>
          <ul className="space-y-1.5">
            {strategy.gaps.map((g, i) => (
              <li key={i} className="text-sm text-slate-300 flex items-start gap-2">
                <span className="w-2 h-2 rounded-full bg-amber-400 mt-1.5 shrink-0" />
                {g}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}

/* ─── Interview Tips Tab ─── */
function TipsTab({ seniorityLevel, title }: { seniorityLevel: string; title: string }) {
  const isSenior = /senior|director|vp|head|chief|lead|principal/i.test(seniorityLevel || title);

  const generalTips = isSenior
    ? [
        'Prepare stories that demonstrate strategic impact and organizational leadership',
        'Quantify your influence: revenue driven, teams scaled, costs reduced',
        'Show how you\'ve navigated ambiguity and made high-stakes decisions',
        'Discuss cross-functional partnerships and executive communication',
        'Demonstrate thought leadership in your domain (publications, talks, mentoring)',
        'Be ready to discuss failures and what you learned from them',
        'Prepare questions about company strategy, culture, and growth plans',
      ]
    : [
        'Research the company\'s recent news, products, and culture thoroughly',
        'Prepare STAR-format stories for common behavioral questions',
        'Practice explaining technical concepts clearly and concisely',
        'Show enthusiasm for the role and alignment with company values',
        'Prepare thoughtful questions about team dynamics and growth opportunities',
        'Be ready to discuss your career trajectory and goals',
        'Follow up with a thank-you email within 24 hours',
      ];

  const behavioralQuestions = isSenior
    ? [
        'Tell me about a time you led a major organizational transformation.',
        'Describe a situation where you had to make a difficult decision with incomplete information.',
        'How have you handled conflict between teams or stakeholders?',
        'Give an example of how you\'ve built and scaled a high-performing team.',
        'Tell me about a project that failed and how you handled the aftermath.',
        'How do you prioritize when everything seems urgent?',
        'Describe your approach to stakeholder management at the executive level.',
        'How have you driven innovation within a large organization?',
      ]
    : [
        'Tell me about a time you overcame a significant challenge at work.',
        'Describe a situation where you had to work with a difficult team member.',
        'Give an example of a project you\'re most proud of and why.',
        'How do you handle tight deadlines and competing priorities?',
        'Tell me about a time you received critical feedback and how you responded.',
        'Describe a situation where you had to learn something quickly.',
        'How do you approach problem-solving when you\'re stuck?',
        'Tell me about a time you went above and beyond in your role.',
      ];

  return (
    <div className="space-y-6">
      <div className="card">
        <h3 className="text-sm font-semibold text-white mb-1">Interview Tips</h3>
        <p className="text-xs text-slate-500 mb-4">
          {isSenior ? 'Senior/Leadership level' : 'Standard level'} interview guidance based on the role seniority
        </p>
        <ul className="space-y-3">
          {generalTips.map((tip, i) => (
            <li key={i} className="text-sm text-slate-300 flex items-start gap-3 bg-[#0E1628] rounded-lg p-3 border border-[#1E2D4A]">
              <Lightbulb className="w-4 h-4 text-amber-400 mt-0.5 shrink-0" />
              {tip}
            </li>
          ))}
        </ul>
      </div>

      <div className="card">
        <h3 className="text-sm font-semibold text-white mb-4">Common Behavioral Questions</h3>
        <ul className="space-y-2">
          {behavioralQuestions.map((q, i) => (
            <li key={i} className="text-sm text-slate-300 bg-blue-500/5 border border-blue-500/10 rounded-lg p-3">
              <span className="text-blue-400 font-mono text-xs mr-2">Q{i + 1}.</span>
              {q}
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
