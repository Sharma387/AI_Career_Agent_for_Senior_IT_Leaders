import { useState } from 'react';
import { api } from '../api/client';

const PROFILE_ID = 1;

export function InterviewPrep() {
  const [jobId, setJobId] = useState('');
  const [materials, setMaterials] = useState<{ cover_letter: string; resume: string } | null>(null);
  const [loading, setLoading] = useState(false);

  const handleGenerate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!jobId) return;
    setLoading(true);
    setMaterials(null);
    try {
      const res = await api.jobs.generateMaterials(Number(jobId), PROFILE_ID);
      setMaterials(res.data);
    } catch {
      alert('Failed to generate materials. Make sure the job ID is valid.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-8 max-w-3xl">
      <h1 className="text-2xl font-bold">Interview Preparation</h1>

      <div className="card">
        <h2 className="text-lg font-semibold mb-4">Generate Materials</h2>
        <form onSubmit={handleGenerate} className="flex items-end gap-4">
          <div className="flex-1">
            <label className="block text-sm font-medium mb-1">Job ID</label>
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
            {loading ? 'Generating...' : 'Generate Materials'}
          </button>
        </form>
      </div>

      {materials && (
        <div className="space-y-6">
          <div className="card">
            <h2 className="text-lg font-semibold mb-4">Cover Letter</h2>
            <div className="bg-gray-50 rounded-lg p-4 whitespace-pre-wrap text-sm text-gray-700">
              {materials.cover_letter}
            </div>
            <button
              onClick={() => navigator.clipboard.writeText(materials.cover_letter)}
              className="btn-secondary text-sm mt-3"
            >
              Copy to Clipboard
            </button>
          </div>

          <div className="card">
            <h2 className="text-lg font-semibold mb-4">Tailored Resume</h2>
            <div className="bg-gray-50 rounded-lg p-4 whitespace-pre-wrap text-sm text-gray-700">
              {materials.resume}
            </div>
            <button
              onClick={() => navigator.clipboard.writeText(materials.resume)}
              className="btn-secondary text-sm mt-3"
            >
              Copy to Clipboard
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
