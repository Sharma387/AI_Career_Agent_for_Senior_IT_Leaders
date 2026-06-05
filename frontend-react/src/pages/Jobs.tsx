import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api/client';
import type { JobPosting, MatchResult } from '../types';

const PROFILE_ID = 1;

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

  useEffect(() => {
    api.jobs.list()
      .then((res) => setJobs(res.data))
      .catch(() => null)
      .finally(() => setLoading(false));
  }, []);

  const handleMatch = async (jobId: number) => {
    setMatching(jobId);
    setMatchResult(null);
    try {
      const res = await api.jobs.match(jobId, PROFILE_ID);
      setMatchResult(res.data);
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

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-bold">Job Opportunities</h1>

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

          {matchResult.gaps.length > 0 && (
            <div className="mt-6 border-t pt-4">
              <h3 className="font-semibold mb-3">Skills Articulation</h3>
              <p className="text-sm text-gray-600 mb-4">
                Review the identified gaps below. If you possess these skills, describe how you demonstrate them.
                Your responses will be used to strengthen your profile and improve future matches.
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
                  onClick={() => {
                    alert('Articulations saved! These will be used to improve your future matches.');
                    setSkillArticulations({});
                  }}
                  className="btn-primary mt-4"
                >
                  Save Articulations
                </button>
              )}
            </div>
          )}
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
