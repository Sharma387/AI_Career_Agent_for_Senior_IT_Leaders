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
  const [generatedMaterials, setGeneratedMaterials] = useState<{ application_id: number; resume: string; cover_letter: string } | null>(null);
  const [generating, setGenerating] = useState<number | null>(null);

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
                {matchResult.evidence.map((e, i) => (
                  <li key={i} className="text-sm text-gray-700">• {e}</li>
                ))}
              </ul>
            </div>
          )}

          <p className="mt-4 text-sm text-gray-600">{matchResult.explanation}</p>
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

          <div className="space-y-4">
            <div>
              <h3 className="font-medium mb-2">Tailored Resume</h3>
              <div className="bg-white rounded-lg p-4 max-h-48 overflow-y-auto text-sm whitespace-pre-wrap">
                {generatedMaterials.resume}
              </div>
              <button
                onClick={() => navigator.clipboard.writeText(generatedMaterials.resume)}
                className="btn-secondary text-sm mt-2"
              >
                Copy Resume
              </button>
            </div>

            <div>
              <h3 className="font-medium mb-2">Cover Letter</h3>
              <div className="bg-white rounded-lg p-4 max-h-48 overflow-y-auto text-sm whitespace-pre-wrap">
                {generatedMaterials.cover_letter}
              </div>
              <button
                onClick={() => navigator.clipboard.writeText(generatedMaterials.cover_letter)}
                className="btn-secondary text-sm mt-2"
              >
                Copy Cover Letter
              </button>
            </div>
          </div>

          <p className="mt-4 text-sm text-gray-600">
            Materials saved to your application. You can edit them from the{' '}
            <Link to="/applications" className="text-blue-600 hover:underline">Applications</Link> page.
          </p>
        </div>
      )}
    </div>
  );
}
