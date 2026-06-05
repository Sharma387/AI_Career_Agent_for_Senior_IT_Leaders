import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api/client';
import type { JobPosting, MatchResult, MatchScoreBreakdown, ImprovementRecommendation, InterviewStrategy } from '../types';

const PROFILE_ID = 1;

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

function ScoreBar({ label, score, max, weight }: { label: string; score: number; max: number; weight: number }) {
  const pct = max > 0 ? (score / max) * 100 : 0;
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-sm">
        <span className="text-gray-700">{label}</span>
        <span className="font-medium">{score}/{max} (×{weight})</span>
      </div>
      <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
        <div className="h-full bg-blue-500 rounded-full transition-all" style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

export function Jobs() {
  const [jobs, setJobs] = useState<JobPosting[]>([]);
  const [loading, setLoading] = useState(true);
  const [matchResult, setMatchResult] = useState<MatchResult | null>(null);
  const [matching, setMatching] = useState<number | null>(null);
  const [newJobText, setNewJobText] = useState('');
  const [adding, setAdding] = useState(false);
  const [generatedMaterials, setGeneratedMaterials] = useState<{
    application_id: number;
    resume: string;
    cover_letter: string;
    resume_html: string;
    cover_letter_html: string;
  } | null>(null);
  const [generating, setGenerating] = useState<number | null>(null);
  const [activeTab, setActiveTab] = useState<'resume' | 'cover_letter'>('resume');
  const [skillArticulations, setSkillArticulations] = useState<Record<number, { hasSkill: boolean; evidence: string }>>({});
  const [currentMatchId, setCurrentMatchId] = useState<number | null>(null);
  const [llmInfo, setLlmInfo] = useState<{ provider: string; model: string } | null>(null);
  const [interviewStrategy, setInterviewStrategy] = useState<InterviewStrategy | null>(null);
  const [loadingStrategy, setLoadingStrategy] = useState<number | null>(null);
  

  useEffect(() => {
    api.jobs.list()
      .then((res) => setJobs(res.data))
      .catch(() => null)
      .finally(() => setLoading(false));
    api.llm.getInfo()
      .then((res) => setLlmInfo(res.data))
      .catch(() => null);
  }, []);

  const handleMatch = async (jobId: number) => {
    setMatching(jobId);
    setMatchResult(null);
    setSkillArticulations({});
    setCurrentMatchId(null);
    setInterviewStrategy(null);

    try {
      const prevRes = await api.match.getPrevious(jobId, PROFILE_ID);
      if (prevRes.data) {
        const saved: SavedMatch = prevRes.data;
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
      } else {
        const res = await api.jobs.matchEnhanced(jobId, PROFILE_ID);
        const data = res.data as any;
        setMatchResult(data);
        setCurrentMatchId(data.match_id ? Number(data.match_id) : null);
      }
    } catch {
      alert('Failed to generate match');
    } finally {
      setMatching(null);
    }
  };

  const handleGenerateMaterials = async (jobId: number) => {
    setGenerating(jobId);
    setGeneratedMaterials(null);
    try {
      const res = await api.jobs.generateMaterials(jobId, PROFILE_ID);
      setGeneratedMaterials(res.data);
      setActiveTab('resume');
    } catch {
      alert('Failed to generate materials');
    } finally {
      setGenerating(null);
    }
  };

  const handleGetInterviewStrategy = async (jobId: number) => {
    setLoadingStrategy(jobId);
    setInterviewStrategy(null);
    try {
      const res = await api.jobs.getInterviewStrategy(jobId, PROFILE_ID);
      setInterviewStrategy(res.data);
    } catch {
      alert('Failed to generate interview strategy');
    } finally {
      setLoadingStrategy(null);
    }
  };

  const handleAddJob = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newJobText.trim()) return;
    setAdding(true);
    try {
      await api.jobs.add(newJobText);
      setNewJobText('');
      const res = await api.jobs.list();
      setJobs(res.data);
    } catch {
      alert('Failed to add job');
    } finally {
      setAdding(false);
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
      alert('Articulations saved! These will be used to improve your future matches.');
    } catch {
      alert('Failed to save articulations');
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
      </div>
    );
  }

  const breakdown: MatchScoreBreakdown | undefined = matchResult?.score_breakdown;
  const recommendations: ImprovementRecommendation[] = matchResult?.improvement_recommendations || [];

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Job Opportunities</h1>
        {llmInfo && (
          <div className="text-xs text-gray-500 bg-gray-100 px-3 py-1 rounded-full">
            LLM: {llmInfo.provider} / {llmInfo.model}
          </div>
        )}
      </div>

      <div className="card">
        <h2 className="text-lg font-semibold mb-4">Add Job Posting</h2>
        <form onSubmit={handleAddJob} className="flex gap-4">
          <textarea
            value={newJobText}
            onChange={(e) => setNewJobText(e.target.value)}
            className="input-field flex-1"
            rows={3}
            placeholder="Paste job description here..."
            required
          />
          <button type="submit" disabled={adding} className="btn-primary self-end whitespace-nowrap disabled:opacity-50">
            {adding ? 'Adding...' : 'Add Job'}
          </button>
        </form>
      </div>

      {jobs.length === 0 ? (
        <div className="card text-center py-12">
          <p className="text-gray-500">No jobs available yet. Add a job posting above to get started.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {jobs.map((job) => (
            <div key={job.id} className="card">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <h3 className="text-lg font-semibold">{job.title}</h3>
                  <p className="text-gray-600">{job.company}</p>
                  <div className="flex items-center gap-3 mt-2 text-sm text-gray-500">
                    <span>{job.location}</span>
                    <span>•</span>
                    <span>{job.seniority_level}</span>
                    <span>•</span>
                    <span>{job.source}</span>
                  </div>
                  <p className="text-gray-700 mt-3 line-clamp-3">{job.description}</p>
                </div>
                <div className="flex items-center gap-2 ml-4">
                  <button
                    onClick={() => handleMatch(job.id)}
                    disabled={matching === job.id}
                    className="btn-primary whitespace-nowrap disabled:opacity-50"
                  >
                    {matching === job.id ? 'Matching...' : 'Match Me'}
                  </button>
                  <button
                    onClick={() => handleGenerateMaterials(job.id)}
                    disabled={generating === job.id}
                    className="btn-secondary whitespace-nowrap disabled:opacity-50"
                  >
                    {generating === job.id ? 'Generating...' : 'Generate Materials'}
                  </button>
                  <button
                    onClick={() => handleGetInterviewStrategy(job.id)}
                    disabled={loadingStrategy === job.id}
                    className="btn-secondary whitespace-nowrap disabled:opacity-50"
                  >
                    {loadingStrategy === job.id ? 'Loading...' : 'AI Interview Strategy'}
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {matchResult && (
        <div className="card border-blue-200 bg-blue-50/50">
          <h2 className="text-lg font-semibold mb-4">Match Result</h2>
          <div className="flex items-center gap-4 mb-4">
            <div className="text-4xl font-bold text-blue-600">{matchResult.match_score}%</div>
            <div>
              <p className="font-medium">Match Score</p>
              <p className="text-sm text-gray-600">{matchResult.recommendation}</p>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-6">
            <div>
              <h3 className="font-medium text-green-700 mb-2">Strengths</h3>
              <ul className="space-y-1">
                {matchResult.strengths.map((s, i) => (
                  <li key={i} className="text-sm text-gray-700">• {s}</li>
                ))}
              </ul>
            </div>
            <div>
              <h3 className="font-medium text-amber-700 mb-2">Gaps</h3>
              <ul className="space-y-1">
                {matchResult.gaps.map((g, i) => (
                  <li key={i} className="text-sm text-gray-700">• {g}</li>
                ))}
              </ul>
            </div>
          </div>

          {matchResult.evidence.length > 0 && (
            <div className="mt-4">
              <h3 className="font-medium mb-2">Evidence</h3>
              <ul className="space-y-1">
                {matchResult.evidence.map((e, i) => {
                  const text = typeof e === 'string' ? e : `${e.career_chunk} — ${e.relevance}`;
                  return <li key={i} className="text-sm text-gray-700">• {text}</li>;
                })}
              </ul>
            </div>
          )}

          <p className="mt-4 text-sm text-gray-600">{matchResult.explanation}</p>

          {/* Score Breakdown */}
          {breakdown && (
            <div className="mt-6 border-t pt-4">
              <h3 className="font-semibold mb-3">Score Breakdown</h3>
              <div className="space-y-3">
                <ScoreBar label="Skills Match" score={breakdown.skills_match.score} max={breakdown.skills_match.max} weight={breakdown.skills_match.weight} />
                <ScoreBar label="Experience Match" score={breakdown.experience_match.score} max={breakdown.experience_match.max} weight={breakdown.experience_match.weight} />
                <ScoreBar label="Industry Relevance" score={breakdown.industry_relevance.score} max={breakdown.industry_relevance.max} weight={breakdown.industry_relevance.weight} />
                <ScoreBar label="Leadership Signals" score={breakdown.leadership_signals.score} max={breakdown.leadership_signals.max} weight={breakdown.leadership_signals.weight} />
              </div>
            </div>
          )}

          {/* Improvement Recommendations */}
          {recommendations.length > 0 && (
            <div className="mt-6 border-t pt-4">
              <h3 className="font-semibold mb-3">Improvement Recommendations</h3>
              <div className="space-y-3">
                {recommendations.map((rec, i) => (
                  <div key={i} className="bg-white rounded-lg p-4 border">
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="font-medium text-sm">{rec.area}</span>
                          <span className={`text-xs px-2 py-0.5 rounded-full ${
                            rec.priority === 'high' ? 'bg-red-100 text-red-700' :
                            rec.priority === 'medium' ? 'bg-yellow-100 text-yellow-700' :
                            'bg-gray-100 text-gray-700'
                          }`}>{rec.priority}</span>
                        </div>
                        <p className="text-sm text-gray-600 mb-1">Gap: {rec.gap}</p>
                        <p className="text-sm text-gray-700">{rec.recommendation}</p>
                        {rec.estimated_impact && (
                          <p className="text-xs text-green-600 mt-1">Estimated impact: {rec.estimated_impact}</p>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {matchResult.gaps.length > 0 && (
            <div className="mt-6 border-t pt-4">
              <h3 className="font-semibold mb-3">Skills Articulation</h3>
              <p className="text-sm text-gray-600 mb-4">
                Review the identified gaps below. If you possess these skills, describe how you demonstrate them.
                Your responses will be saved and used to strengthen your profile for future matches.
              </p>
              <div className="space-y-4">
                {matchResult.gaps.map((gap, i) => (
                  <div key={i} className="bg-white rounded-lg p-4 border">
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <p className="font-medium text-sm">{gap}</p>
                        <div className="flex items-center gap-4 mt-2">
                          <label className="flex items-center gap-2 text-sm">
                            <input
                              type="radio"
                              name={`skill-${i}`}
                              checked={skillArticulations[i]?.hasSkill === true}
                              onChange={() => setSkillArticulations(prev => ({ ...prev, [i]: { hasSkill: true, evidence: prev[i]?.evidence || '' } }))}
                            />
                            I have this skill
                          </label>
                          <label className="flex items-center gap-2 text-sm">
                            <input
                              type="radio"
                              name={`skill-${i}`}
                              checked={skillArticulations[i]?.hasSkill === false}
                              onChange={() => setSkillArticulations(prev => ({ ...prev, [i]: { hasSkill: false, evidence: '' } }))}
                            />
                            I don't have this yet
                          </label>
                        </div>
                        {skillArticulations[i]?.hasSkill && (
                          <textarea
                            value={skillArticulations[i]?.evidence || ''}
                            onChange={(e) => setSkillArticulations(prev => ({ ...prev, [i]: { ...prev[i], evidence: e.target.value } }))}
                            className="input-field w-full mt-2"
                            rows={3}
                            placeholder="Describe how you demonstrate this skill (e.g., specific projects, achievements, examples)..."
                          />
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
              {Object.keys(skillArticulations).length > 0 && (
                <button
                  onClick={handleSaveArticulations}
                  className="btn-primary mt-4"
                >
                  Save Articulations
                </button>
              )}
            </div>
          )}
        </div>
      )}

      {/* Interview Strategy */}
      {interviewStrategy && (
        <div className="card border-purple-200 bg-purple-50/50">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold">AI Interview Strategy</h2>
            <button onClick={() => setInterviewStrategy(null)} className="text-gray-500 hover:text-gray-700 text-xl">×</button>
          </div>

          <div className="flex items-center gap-4 mb-4">
            <div className="text-3xl font-bold text-purple-600">{interviewStrategy.match_score}%</div>
            <div>
              <p className="font-medium">Match Score</p>
              <p className="text-sm text-gray-600">{interviewStrategy.recommendation}</p>
            </div>
          </div>

          <p className="text-sm text-gray-600 mb-4">{interviewStrategy.explanation}</p>

          {/* Key Themes */}
          {interviewStrategy.key_themes.length > 0 && (
            <div className="mb-4">
              <h3 className="font-medium text-purple-700 mb-2">Key Themes</h3>
              <div className="flex flex-wrap gap-2">
                {interviewStrategy.key_themes.map((theme, i) => (
                  <span key={i} className="bg-purple-100 text-purple-700 px-3 py-1 rounded-full text-sm">{theme}</span>
                ))}
              </div>
            </div>
          )}

          {/* Potential Questions */}
          {interviewStrategy.potential_questions.length > 0 && (
            <div className="mb-4">
              <h3 className="font-medium text-blue-700 mb-2">Potential Questions</h3>
              <ul className="space-y-1">
                {interviewStrategy.potential_questions.map((q, i) => (
                  <li key={i} className="text-sm text-gray-700 bg-blue-50 rounded p-2">• {q}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Talking Points */}
          {interviewStrategy.talking_points.length > 0 && (
            <div className="mb-4">
              <h3 className="font-medium text-green-700 mb-2">Talking Points</h3>
              <ul className="space-y-1">
                {interviewStrategy.talking_points.map((tp, i) => (
                  <li key={i} className="text-sm text-gray-700 bg-green-50 rounded p-2">• {tp}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Areas to Prepare */}
          {interviewStrategy.areas_to_prepare.length > 0 && (
            <div className="mb-4">
              <h3 className="font-medium text-amber-700 mb-2">Areas to Prepare</h3>
              <ul className="space-y-1">
                {interviewStrategy.areas_to_prepare.map((a, i) => (
                  <li key={i} className="text-sm text-gray-700 bg-amber-50 rounded p-2">• {a}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Strengths & Gaps Summary */}
          <div className="grid grid-cols-2 gap-4 mt-4 border-t pt-4">
            <div>
              <h3 className="font-medium text-green-700 mb-2">Strengths</h3>
              <ul className="space-y-1">
                {interviewStrategy.strengths.map((s, i) => (
                  <li key={i} className="text-sm text-gray-700">• {s}</li>
                ))}
              </ul>
            </div>
            <div>
              <h3 className="font-medium text-amber-700 mb-2">Gaps</h3>
              <ul className="space-y-1">
                {interviewStrategy.gaps.map((g, i) => (
                  <li key={i} className="text-sm text-gray-700">• {g}</li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}

      {generatedMaterials && (
        <div className="card border-green-200 bg-green-50/50">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold">Generated Materials</h2>
            <Link to="/applications" className="text-sm text-blue-600 hover:text-blue-700">
              View in Applications →
            </Link>
          </div>

          <div className="flex gap-2 mb-4 border-b">
            <button
              onClick={() => setActiveTab('resume')}
              className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                activeTab === 'resume'
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              Resume
            </button>
            <button
              onClick={() => setActiveTab('cover_letter')}
              className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                activeTab === 'cover_letter'
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              Cover Letter
            </button>
          </div>

          {activeTab === 'resume' ? (
            <div>
              <div
                className="bg-white rounded-lg p-6 border max-h-96 overflow-y-auto"
                dangerouslySetInnerHTML={{ __html: generatedMaterials.resume_html }}
              />
              <div className="flex gap-2 mt-4">
                <a
                  href={api.applications.downloadResumeHtml(generatedMaterials.application_id)}
                  download
                  className="btn-secondary text-sm"
                >
                  Download HTML
                </a>
                <a
                  href={api.applications.downloadResumeDocx(generatedMaterials.application_id)}
                  download
                  className="btn-primary text-sm"
                >
                  Download Word (.docx)
                </a>
              </div>
            </div>
          ) : (
            <div>
              <div
                className="bg-white rounded-lg p-6 border max-h-96 overflow-y-auto"
                dangerouslySetInnerHTML={{ __html: generatedMaterials.cover_letter_html }}
              />
              <div className="flex gap-2 mt-4">
                <a
                  href={api.applications.downloadCoverLetterHtml(generatedMaterials.application_id)}
                  download
                  className="btn-secondary text-sm"
                >
                  Download HTML
                </a>
                <a
                  href={api.applications.downloadCoverLetterDocx(generatedMaterials.application_id)}
                  download
                  className="btn-primary text-sm"
                >
                  Download Word (.docx)
                </a>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
