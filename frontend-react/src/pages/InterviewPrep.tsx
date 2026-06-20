import { useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api/client';
import { useAuth } from '../context/AuthContext';
import { MessageSquare, Copy } from 'lucide-react';

export function InterviewPrep() {
  const { profileId } = useAuth();
  const [jobId, setJobId] = useState('');
  const [materials, setMaterials] = useState<{ cover_letter: string; resume: string } | null>(null);
  const [loading, setLoading] = useState(false);

  const handleGenerate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!jobId) return;
    setLoading(true);
    setMaterials(null);
    try {
      const res = await api.jobs.generateMaterials(Number(jobId), profileId!);
      setMaterials(res.data);
    } catch {
      alert('Failed to generate materials. Make sure the job ID is valid.');
    } finally {
      setLoading(false);
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

  return (
    <div className="space-y-6 max-w-3xl">
      <h1 className="text-2xl font-bold text-white">Interview Preparation</h1>

      <div className="card">
        <div className="flex items-center gap-2 mb-4">
          <MessageSquare className="w-4 h-4 text-purple-400" />
          <h2 className="text-sm font-semibold text-white">Generate Materials</h2>
        </div>
        <form onSubmit={handleGenerate} className="flex items-end gap-4">
          <div className="flex-1">
            <label className="block text-xs font-medium text-slate-400 mb-1.5">Job ID</label>
            <input
              type="number"
              value={jobId}
              onChange={(e) => setJobId(e.target.value)}
              className="input-field"
              placeholder="Enter job ID"
              required
            />
          </div>
          <button type="submit" disabled={loading} className="btn-primary disabled:opacity-50 whitespace-nowrap">
            {loading ? 'Generating...' : 'Generate'}
          </button>
        </form>
      </div>

      {materials && (
        <div className="space-y-4">
          <div className="card">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-semibold text-white">Cover Letter</h2>
              <button
                onClick={() => navigator.clipboard.writeText(materials.cover_letter)}
                className="btn-ghost text-xs"
              >
                <Copy className="w-3 h-3 mr-1" /> Copy
              </button>
            </div>
            <div className="bg-[#0E1628] rounded-lg p-4 border border-[#1E2D4A] max-h-80 overflow-y-auto">
              <p className="text-xs text-slate-300 whitespace-pre-wrap font-mono leading-relaxed">
                {materials.cover_letter}
              </p>
            </div>
          </div>

          <div className="card">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-semibold text-white">Tailored Resume</h2>
              <button
                onClick={() => navigator.clipboard.writeText(materials.resume)}
                className="btn-ghost text-xs"
              >
                <Copy className="w-3 h-3 mr-1" /> Copy
              </button>
            </div>
            <div className="bg-[#0E1628] rounded-lg p-4 border border-[#1E2D4A] max-h-80 overflow-y-auto">
              <p className="text-xs text-slate-300 whitespace-pre-wrap font-mono leading-relaxed">
                {materials.resume}
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
