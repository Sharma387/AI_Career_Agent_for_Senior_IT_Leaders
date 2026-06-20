import { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { api } from '../api/client';
import { useAuth } from '../context/AuthContext';
import { Plus, ChevronRight } from 'lucide-react';
import { toast } from 'sonner';
import type { JobPosting } from '../types';

export function Jobs() {
  const { profileId } = useAuth();
  const navigate = useNavigate();
  const [jobs, setJobs] = useState<JobPosting[]>([]);
  const [loading, setLoading] = useState(true);
  const [newJobText, setNewJobText] = useState('');
  const [adding, setAdding] = useState(false);
  const [matchScores, setMatchScores] = useState<Record<number, number>>({});

  useEffect(() => {
    api.jobs.list()
      .then((res) => {
        // Only show manually added jobs
        const manualJobs = res.data.filter((j: JobPosting) => j.source === 'manual');
        setJobs(manualJobs);
      })
      .catch(() => null)
      .finally(() => setLoading(false));
  }, []);

  // Load previous match scores for manual jobs
  useEffect(() => {
    if (!profileId || jobs.length === 0) return;
    const loadScores = async () => {
      const scores: Record<number, number> = {};
      for (const job of jobs) {
        try {
          const res = await api.match.getPrevious(job.id, profileId);
          if (res.data && res.data.match_score) {
            scores[job.id] = res.data.match_score;
          }
        } catch {
          // No match for this job
        }
      }
      setMatchScores(scores);
    };
    loadScores();
  }, [jobs, profileId]);

  const handleAddJob = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newJobText.trim()) return;
    setAdding(true);
    try {
      await api.jobs.add(newJobText, 'manual');
      setNewJobText('');
      const res = await api.jobs.list();
      const manualJobs = res.data.filter((j: JobPosting) => j.source === 'manual');
      setJobs(manualJobs);
      toast.success('Job added successfully!');
    } catch {
      toast.error('Failed to add job');
    } finally {
      setAdding(false);
    }
  };

  if (!profileId) {
    return (
      <div className="card text-center py-12">
        <p className="text-slate-400 mb-4">Upload your resume first to get started.</p>
        <Link to="/resume" className="btn-primary">Upload Resume</Link>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white">My Jobs</h1>
        <span className="text-xs text-slate-500 font-mono">{jobs.length} job{jobs.length !== 1 ? 's' : ''}</span>
      </div>

      {/* Add Job Posting */}
      <div className="card">
        <div className="flex items-center gap-2 mb-4">
          <Plus className="w-4 h-4 text-blue-400" />
          <h2 className="text-sm font-semibold text-white">Add Job Posting</h2>
        </div>
        <p className="text-xs text-slate-500 mb-3">
          Paste a full job description below. For best match results, include the complete posting text.
        </p>
        <form onSubmit={handleAddJob} className="flex gap-4">
          <textarea
            value={newJobText}
            onChange={(e) => setNewJobText(e.target.value)}
            className="input-field flex-1 min-h-[80px] resize-y"
            rows={3}
            placeholder="Paste full job description here..."
            required
          />
          <button type="submit" disabled={adding} className="btn-primary self-end whitespace-nowrap disabled:opacity-50">
            {adding ? 'Adding...' : 'Add Job'}
          </button>
        </form>
      </div>

      {/* Job List */}
      {jobs.length === 0 ? (
        <div className="card text-center py-12">
          <p className="text-slate-500 mb-2">No jobs in your pipeline yet.</p>
          <p className="text-xs text-slate-600">
            Add jobs manually above, or browse and add from the{' '}
            <Link to="/discover" className="text-blue-400 hover:text-blue-300 underline">Discover</Link> page.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {jobs.map((job) => (
            <div
              key={job.id}
              onClick={() => navigate(`/jobs/${job.id}`, { state: { job } })}
              className="card hover:border-blue-500/30 transition-all duration-200 cursor-pointer group"
            >
              <div className="flex items-center gap-4">
                {/* Match score circle */}
                {matchScores[job.id] !== undefined && (
                  <div className="shrink-0">
                    <div className={`w-11 h-11 rounded-full flex items-center justify-center text-xs font-bold border-2 ${
                      matchScores[job.id] >= 75
                        ? 'border-emerald-500 text-emerald-400 bg-emerald-500/10'
                        : matchScores[job.id] >= 50
                        ? 'border-amber-500 text-amber-400 bg-amber-500/10'
                        : 'border-red-500 text-red-400 bg-red-500/10'
                    }`}>
                      {matchScores[job.id]}%
                    </div>
                  </div>
                )}

                <div className="flex-1 min-w-0">
                  <h3 className="text-sm font-semibold text-white truncate group-hover:text-blue-400 transition-colors">{job.title}</h3>
                  <p className="text-slate-400 text-sm">{job.company}</p>
                  <div className="flex flex-wrap items-center gap-2 mt-2">
                    {job.location && <span className="text-[11px] px-2 py-0.5 rounded bg-[#0E1628] border border-[#1E2D4A] text-slate-400">{job.location}</span>}
                    {job.created_at && (
                      <span className="text-[11px] text-slate-600 font-mono">
                        Added {new Date(job.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
                      </span>
                    )}
                  </div>
                </div>

                <ChevronRight className="w-5 h-5 text-slate-600 group-hover:text-blue-400 transition-colors shrink-0" />
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
