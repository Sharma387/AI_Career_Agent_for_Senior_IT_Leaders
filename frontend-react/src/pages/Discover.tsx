import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api/client';
import { useAuth } from '../context/AuthContext';
import { Search, ExternalLink, Plus, X } from 'lucide-react';
import { toast } from 'sonner';
import type { JobPosting } from '../types';

export function Discover() {
  const { profileId } = useAuth();
  const [jobs, setJobs] = useState<JobPosting[]>([]);
  const [loading, setLoading] = useState(true);
  const [llmInfo, setLlmInfo] = useState<{ provider: string; model: string } | null>(null);
  const [scraping, setScraping] = useState(false);
  const [targetRole, setTargetRole] = useState('project-manager');
  const [customKeywords, setCustomKeywords] = useState('');
  const [searchLocation, setSearchLocation] = useState('');
  const [industry, setIndustry] = useState('');
  const [apiUsage, setApiUsage] = useState<{ monthly_calls: number; monthly_limit: number; remaining: number; searches_today: number; quota_exhausted: boolean } | null>(null);
  const [filterSource, setFilterSource] = useState('all');
  const [filterSeniority, setFilterSeniority] = useState('all');
  const [filterLocation, setFilterLocation] = useState('');
  const [filterSort, setFilterSort] = useState<'newest' | 'oldest' | 'company'>('newest');
  const [filterSalaryOnly, setFilterSalaryOnly] = useState(false);

  // Modal state
  const [modalOpen, setModalOpen] = useState(false);
  const [modalJob, setModalJob] = useState<JobPosting | null>(null);
  const [modalText, setModalText] = useState('');
  const [addingToMyJobs, setAddingToMyJobs] = useState(false);

  const ROLE_PRESETS: Record<string, { label: string; keywords: string }> = {
    'project-manager': { label: 'Project Manager', keywords: 'project manager' },
    'sr-project-manager': { label: 'Senior Project Manager', keywords: 'senior project manager' },
    'it-manager': { label: 'IT Manager', keywords: 'IT manager' },
    'engineering-manager': { label: 'Engineering Manager', keywords: 'engineering manager' },
    'it-director': { label: 'IT Director / Head of IT', keywords: 'IT director' },
    'cto': { label: 'CTO / VP Engineering', keywords: 'CTO' },
    'scrum-master': { label: 'Scrum Master / Agile Coach', keywords: 'scrum master' },
    'business-analyst': { label: 'Business Analyst', keywords: 'business analyst IT' },
    'custom': { label: 'Custom Search', keywords: '' },
  };

  const INDUSTRY_OPTIONS = [
    'Not Specified',
    'Information Technology',
    'Healthcare & Medical',
    'Financial Services & Banking',
    'Engineering & Construction',
    'Government & Public Sector',
    'Education & Training',
    'Telecommunications',
    'Energy & Utilities',
    'Manufacturing',
    'Retail & Consumer',
    'Media & Entertainment',
    'Professional Services & Consulting',
    'Transport & Logistics',
    'Mining & Resources',
    'Agriculture & Environment',
  ];

  useEffect(() => {
    api.jobs.list()
      .then((res) => setJobs(res.data))
      .catch(() => null)
      .finally(() => setLoading(false));
    api.llm.getInfo()
      .then((res) => setLlmInfo(res.data))
      .catch(() => null);
    api.jobs.getSearchUsage()
      .then((res) => setApiUsage(res.data))
      .catch(() => null);
  }, []);

  const handleTriggerScrape = async () => {
    const preset = ROLE_PRESETS[targetRole];
    const keywords = targetRole === 'custom' ? customKeywords : preset.keywords;

    if (!keywords.trim()) {
      toast.error('Please enter search keywords');
      return;
    }

    const finalKeywords = industry && industry !== 'Not Specified' && industry !== '' ? `${keywords} ${industry}` : keywords;

    setScraping(true);
    try {
      const res = await api.jobs.triggerScrape({
        source: 'adzuna',
        keywords: finalKeywords,
        location: searchLocation,
        hours: undefined
      });

      const [jobsRes, usageRes] = await Promise.all([
        api.jobs.list(),
        api.jobs.getSearchUsage()
      ]);
      setJobs(jobsRes.data);
      setApiUsage(usageRes.data);

      const newJobs = res.data.new_jobs || 0;
      const message = res.data.message;
      if (message) {
        toast.info(message);
      } else if (newJobs > 0) {
        toast.success(`Found ${newJobs} new job${newJobs > 1 ? 's' : ''}!`);
      } else {
        toast.info(`No new jobs found. ${res.data.duplicates || 0} already in your list.`);
      }
    } catch (error: any) {
      toast.error(`Failed to fetch jobs: ${error.response?.data?.detail || error.message}`);
    } finally {
      setScraping(false);
    }
  };

  const handleOpenAddModal = (job: JobPosting) => {
    setModalJob(job);
    const snippet = job.description || '';
    setModalText(snippet ? `${snippet}\n\n[Paste full job description here]` : '[Paste full job description here]');
    setModalOpen(true);
  };

  const handleAddToMyJobs = async () => {
    if (!modalText.trim()) {
      toast.error('Please paste the full job description');
      return;
    }
    setAddingToMyJobs(true);
    try {
      await api.jobs.add(modalText, 'manual');
      toast.success(`"${modalJob?.title}" added to My Jobs!`);
      setModalOpen(false);
      setModalJob(null);
      setModalText('');
    } catch {
      toast.error('Failed to add job');
    } finally {
      setAddingToMyJobs(false);
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

  // Apply filters
  let filtered = [...jobs];
  if (filterSource !== 'all') filtered = filtered.filter(j => j.source === filterSource);
  if (filterSeniority !== 'all') filtered = filtered.filter(j => j.seniority_level === filterSeniority);
  if (filterLocation) filtered = filtered.filter(j => j.location?.toLowerCase().includes(filterLocation.toLowerCase()));
  if (filterSalaryOnly) filtered = filtered.filter(j => j.salary_range && j.salary_range.trim() !== '');
  if (filterSort === 'newest') filtered.sort((a, b) => (b.created_at || '').localeCompare(a.created_at || ''));
  if (filterSort === 'oldest') filtered.sort((a, b) => (a.created_at || '').localeCompare(b.created_at || ''));
  if (filterSort === 'company') filtered.sort((a, b) => (a.company || '').localeCompare(b.company || ''));

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white">Discover Jobs</h1>
        <div className="flex gap-3 items-center">
          {llmInfo && (
            <div className="text-xs text-slate-500 bg-[#0E1628] border border-[#1E2D4A] px-3 py-1.5 rounded-full font-mono">
              {llmInfo.provider}/{llmInfo.model}
            </div>
          )}
          {apiUsage && (
            <div className={`text-xs px-3 py-1.5 rounded-full font-mono border ${apiUsage.remaining < 20 ? 'bg-red-500/10 text-red-400 border-red-500/20' : 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'}`}>
              API: {apiUsage.remaining}/{apiUsage.monthly_limit}
            </div>
          )}
        </div>
      </div>

      {/* Fetch New Jobs Panel */}
      <div className="card">
        <div className="flex items-center gap-2 mb-4">
          <Search className="w-4 h-4 text-blue-400" />
          <h2 className="text-sm font-semibold text-white">Fetch New Jobs</h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-4">
          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1.5">Target Role</label>
            <select
              value={targetRole}
              onChange={(e) => setTargetRole(e.target.value)}
              className="input-field w-full"
            >
              {Object.entries(ROLE_PRESETS).map(([key, { label }]) => (
                <option key={key} value={key}>{label}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1.5">Industry</label>
            <select
              value={industry}
              onChange={(e) => setIndustry(e.target.value)}
              className="input-field w-full"
            >
              {INDUSTRY_OPTIONS.map((opt) => (
                <option key={opt} value={opt}>{opt}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1.5">Location (optional)</label>
            <input
              type="text"
              value={searchLocation}
              onChange={(e) => setSearchLocation(e.target.value)}
              className="input-field w-full"
              placeholder="e.g. Auckland, Sydney"
            />
          </div>

          <div className="flex items-end">
            <button
              onClick={handleTriggerScrape}
              disabled={scraping || (targetRole === 'custom' && !customKeywords.trim())}
              className="btn-gold w-full disabled:opacity-50"
            >
              {scraping ? 'Searching...' : 'Fetch New Jobs'}
            </button>
          </div>
        </div>

        {targetRole === 'custom' && (
          <div className="mb-4">
            <label className="block text-xs font-medium text-slate-400 mb-1.5">Custom Keywords</label>
            <input
              type="text"
              value={customKeywords}
              onChange={(e) => setCustomKeywords(e.target.value)}
              className="input-field w-full"
              placeholder='"Scrum Master" OR "Agile Coach"'
            />
          </div>
        )}

        {apiUsage && (
          <div className="flex items-center gap-4 text-xs text-slate-500 font-mono">
            <span>Searches: {apiUsage.searches_today}</span>
            <span className="text-[#1E2D4A]">·</span>
            <span>Monthly: {apiUsage.monthly_calls}/{apiUsage.monthly_limit}</span>
            {apiUsage.quota_exhausted && (
              <>
                <span className="text-[#1E2D4A]">·</span>
                <span className="text-amber-400">Free fallback active</span>
              </>
            )}
          </div>
        )}
      </div>

      {/* Job List */}
      {jobs.length === 0 ? (
        <div className="card text-center py-12">
          <p className="text-slate-500">No jobs fetched yet. Use the panel above to search for jobs.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {/* Filters */}
          <div className="card bg-[#0E1628]">
            <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
              <div>
                <label className="block text-[10px] font-medium text-slate-500 uppercase tracking-wider mb-1">Source</label>
                <select value={filterSource} onChange={(e) => setFilterSource(e.target.value)} className="input-field w-full text-sm py-1.5">
                  <option value="all">All Sources</option>
                  {[...new Set(jobs.map(j => j.source))].map(src => (
                    <option key={src} value={src}>{src}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-[10px] font-medium text-slate-500 uppercase tracking-wider mb-1">Seniority</label>
                <select value={filterSeniority} onChange={(e) => setFilterSeniority(e.target.value)} className="input-field w-full text-sm py-1.5">
                  <option value="all">All Levels</option>
                  {[...new Set(jobs.map(j => j.seniority_level).filter(Boolean))].map(level => (
                    <option key={level} value={level}>{level}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-[10px] font-medium text-slate-500 uppercase tracking-wider mb-1">Location</label>
                <input
                  type="text"
                  value={filterLocation}
                  onChange={(e) => setFilterLocation(e.target.value)}
                  className="input-field w-full text-sm py-1.5"
                  placeholder="Filter..."
                />
              </div>
              <div>
                <label className="block text-[10px] font-medium text-slate-500 uppercase tracking-wider mb-1">Sort</label>
                <select value={filterSort} onChange={(e) => setFilterSort(e.target.value as any)} className="input-field w-full text-sm py-1.5">
                  <option value="newest">Newest First</option>
                  <option value="oldest">Oldest First</option>
                  <option value="company">By Company</option>
                </select>
              </div>
              <div className="flex items-end">
                <label className="flex items-center gap-2 text-xs text-slate-400 cursor-pointer">
                  <input type="checkbox" checked={filterSalaryOnly} onChange={(e) => setFilterSalaryOnly(e.target.checked)} className="rounded border-[#1E2D4A] bg-[#0E1628]" />
                  Has Salary
                </label>
              </div>
            </div>
          </div>

          <p className="text-xs text-slate-500 font-mono">{filtered.length} of {jobs.length} job{jobs.length !== 1 ? 's' : ''}</p>

          {filtered.map((job) => (
            <div
              key={job.id}
              className="card hover:border-[#2A3B5A] transition-all duration-200"
            >
              <div className="flex items-start gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <h3 className="text-sm font-semibold text-white truncate">{job.title}</h3>
                  </div>
                  <p className="text-slate-400 text-sm">{job.company}</p>
                  <div className="flex flex-wrap items-center gap-2 mt-2">
                    {job.location && <span className="text-[11px] px-2 py-0.5 rounded bg-[#0E1628] border border-[#1E2D4A] text-slate-400">{job.location}</span>}
                    {job.seniority_level && <span className="text-[11px] px-2 py-0.5 rounded bg-blue-500/10 border border-blue-500/20 text-blue-400">{job.seniority_level}</span>}
                    {job.salary_range && <span className="text-[11px] px-2 py-0.5 rounded bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">{job.salary_range}</span>}
                    <span className="text-[10px] text-slate-600 font-mono">{job.source}</span>
                    {job.created_at && (
                      <span className="text-[11px] px-2 py-0.5 rounded bg-purple-500/10 border border-purple-500/20 text-purple-400">
                        {new Date(job.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
                      </span>
                    )}
                  </div>
                  {job.description && (
                    <p className="text-slate-500 text-xs mt-2 line-clamp-2">{job.description}</p>
                  )}
                </div>
                <div className="flex flex-col gap-2 shrink-0">
                  {job.url && (
                    <a
                      href={job.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="btn-ghost text-xs whitespace-nowrap"
                    >
                      View on Portal <ExternalLink className="w-3 h-3 ml-1" />
                    </a>
                  )}
                  <button
                    onClick={() => handleOpenAddModal(job)}
                    className="btn-primary text-xs whitespace-nowrap"
                  >
                    <Plus className="w-3 h-3 mr-1" /> Add to My Jobs
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Add to My Jobs Modal */}
      {modalOpen && modalJob && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center">
          {/* Backdrop */}
          <div
            className="absolute inset-0 bg-black/70 backdrop-blur-sm"
            onClick={() => setModalOpen(false)}
          />
          {/* Modal */}
          <div className="relative w-full max-w-lg mx-4 bg-[#131B2E] border border-[#1E2D4A] rounded-xl shadow-2xl p-6 animate-fade-in">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-white">Add to My Jobs</h3>
              <button
                onClick={() => setModalOpen(false)}
                className="text-slate-400 hover:text-white transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Read-only job info */}
            <div className="space-y-2 mb-4">
              <div>
                <label className="block text-[10px] font-medium text-slate-500 uppercase tracking-wider mb-0.5">Title</label>
                <p className="text-sm text-slate-200 bg-[#0E1628] border border-[#1E2D4A] rounded-lg px-3 py-2">{modalJob.title}</p>
              </div>
              <div>
                <label className="block text-[10px] font-medium text-slate-500 uppercase tracking-wider mb-0.5">Company</label>
                <p className="text-sm text-slate-200 bg-[#0E1628] border border-[#1E2D4A] rounded-lg px-3 py-2">{modalJob.company}</p>
              </div>
            </div>

            {/* Textarea for full JD */}
            <div className="mb-4">
              <label className="block text-xs font-medium text-slate-400 mb-1.5">
                Full Job Description
              </label>
              <p className="text-[11px] text-slate-500 mb-2">
                Paste the full job description from the portal below. The more detail, the better the match analysis.
              </p>
              <textarea
                value={modalText}
                onChange={(e) => setModalText(e.target.value)}
                className="input-field w-full min-h-[200px] resize-y font-mono text-xs"
                rows={10}
                placeholder="Paste the full job description here..."
              />
            </div>

            {/* Actions */}
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setModalOpen(false)}
                className="btn-ghost text-sm"
              >
                Cancel
              </button>
              <button
                onClick={handleAddToMyJobs}
                disabled={addingToMyJobs || !modalText.trim()}
                className="btn-primary text-sm disabled:opacity-50"
              >
                {addingToMyJobs ? 'Adding...' : 'Add to My Jobs'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
