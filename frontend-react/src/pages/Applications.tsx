import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api/client';
import type { Application, ApplicationStats } from '../types';

const PROFILE_ID = 1;

interface Materials {
  application_id: number;
  resume_version_text: string;
  cover_letter_text: string;
  job_title: string;
  company: string;
}

export function Applications() {
  const [applications, setApplications] = useState<Application[]>([]);
  const [stats, setStats] = useState<ApplicationStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [viewingMaterials, setViewingMaterials] = useState<Materials | null>(null);
  const [loadingMaterials, setLoadingMaterials] = useState<number | null>(null);
  const [editing, setEditing] = useState(false);
  const [editResume, setEditResume] = useState('');
  const [editCoverLetter, setEditCoverLetter] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    Promise.all([api.applications.list(PROFILE_ID), api.applications.getStats(PROFILE_ID)])
      .then(([appsRes, statsRes]) => {
        setApplications(appsRes.data);
        setStats(statsRes.data);
      })
      .catch(() => null)
      .finally(() => setLoading(false));
  }, []);

  const handleStatusUpdate = async (appId: number, newStatus: string) => {
    try {
      await api.applications.updateStatus(appId, newStatus);
      setApplications(applications.map(app =>
        app.application_id === appId ? { ...app, status: newStatus, last_updated: new Date().toISOString() } : app
      ));
    } catch {
      alert('Failed to update status');
    }
  };

  const handleViewMaterials = async (applicationId: number) => {
    setLoadingMaterials(applicationId);
    try {
      const res = await api.applications.getMaterials(applicationId);
      setViewingMaterials(res.data);
      setEditResume(res.data.resume_version_text);
      setEditCoverLetter(res.data.cover_letter_text);
      setEditing(false);
    } catch {
      alert('No materials found for this application');
    } finally {
      setLoadingMaterials(null);
    }
  };

  const handleSaveMaterials = async () => {
    if (!viewingMaterials) return;
    setSaving(true);
    try {
      await api.applications.updateMaterials(viewingMaterials.application_id, editResume, editCoverLetter);
      setViewingMaterials({
        ...viewingMaterials,
        resume_version_text: editResume,
        cover_letter_text: editCoverLetter,
      });
      setEditing(false);
      alert('Materials saved');
    } catch {
      alert('Failed to save materials');
    } finally {
      setSaving(false);
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
      <h1 className="text-2xl font-bold">Applications</h1>

      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          <StatMini label="Applied" value={stats.total_applied} />
          <StatMini label="Interviews" value={stats.interview_count} />
          <StatMini label="Rejected" value={stats.rejection_count} />
          <StatMini label="Offers" value={stats.offer_count} />
          <StatMini label="Interview Rate" value={`${stats.interview_rate}%`} />
        </div>
      )}

      {applications.length === 0 ? (
        <div className="card text-center py-12">
          <p className="text-gray-500 mb-4">No applications tracked yet.</p>
          <Link to="/jobs" className="btn-primary">Browse Jobs</Link>
        </div>
      ) : (
        <div className="space-y-4">
          {applications.map((app) => (
            <div key={app.application_id} className="card">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <h3 className="font-semibold">{app.job.title}</h3>
                  <p className="text-gray-600">{app.job.company} • {app.job.location}</p>
                  <div className="flex items-center gap-4 mt-2 text-sm text-gray-500">
                    <span>Applied: {new Date(app.date_applied).toLocaleDateString()}</span>
                    <span>Updated: {new Date(app.last_updated).toLocaleDateString()}</span>
                  </div>
                  {app.feedback_notes && (
                    <p className="mt-2 text-sm text-gray-600 italic">"{app.feedback_notes}"</p>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  {app.has_materials && (
                    <button
                      onClick={() => handleViewMaterials(app.application_id)}
                      disabled={loadingMaterials === app.application_id}
                      className="text-sm text-blue-600 hover:text-blue-700 disabled:opacity-50"
                    >
                      {loadingMaterials === app.application_id ? 'Loading...' : 'View Materials'}
                    </button>
                  )}
                  <select
                    value={app.status}
                    onChange={(e) => handleStatusUpdate(app.application_id, e.target.value)}
                    className="text-sm border rounded px-2 py-1"
                  >
                    <option value="applied">Applied</option>
                    <option value="interview">Interview</option>
                    <option value="offer">Offer</option>
                    <option value="rejected">Rejected</option>
                    <option value="withdrawn">Withdrawn</option>
                  </select>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {viewingMaterials && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl max-w-4xl w-full max-h-[90vh] overflow-y-auto p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-bold">
                Materials for {viewingMaterials.job_title} @ {viewingMaterials.company}
              </h2>
              <div className="flex items-center gap-2">
                {!editing && (
                  <button onClick={() => setEditing(true)} className="btn-secondary text-sm">
                    Edit
                  </button>
                )}
                <button onClick={() => setViewingMaterials(null)} className="text-gray-500 hover:text-gray-700 text-xl">
                  ×
                </button>
              </div>
            </div>

            <div className="space-y-6">
              <div>
                <h3 className="font-semibold mb-2">Tailored Resume</h3>
                {editing ? (
                  <textarea
                    value={editResume}
                    onChange={(e) => setEditResume(e.target.value)}
                    className="input-field w-full"
                    rows={15}
                  />
                ) : (
                  <div className="bg-gray-50 rounded-lg p-4 whitespace-pre-wrap text-sm max-h-64 overflow-y-auto">
                    {viewingMaterials.resume_version_text || 'No resume generated yet'}
                  </div>
                )}
              </div>

              <div>
                <h3 className="font-semibold mb-2">Cover Letter</h3>
                {editing ? (
                  <textarea
                    value={editCoverLetter}
                    onChange={(e) => setEditCoverLetter(e.target.value)}
                    className="input-field w-full"
                    rows={10}
                  />
                ) : (
                  <div className="bg-gray-50 rounded-lg p-4 whitespace-pre-wrap text-sm max-h-48 overflow-y-auto">
                    {viewingMaterials.cover_letter_text || 'No cover letter generated yet'}
                  </div>
                )}
              </div>

              {editing && (
                <div className="flex justify-end gap-2">
                  <button onClick={() => { setEditing(false); setEditResume(viewingMaterials.resume_version_text); setEditCoverLetter(viewingMaterials.cover_letter_text); }} className="btn-secondary">
                    Cancel
                  </button>
                  <button onClick={handleSaveMaterials} disabled={saving} className="btn-primary disabled:opacity-50">
                    {saving ? 'Saving...' : 'Save Changes'}
                  </button>
                </div>
              )}

              {!editing && (
                <div className="flex justify-end gap-2">
                  <button
                    onClick={() => navigator.clipboard.writeText(viewingMaterials.resume_version_text)}
                    className="btn-secondary text-sm"
                  >
                    Copy Resume
                  </button>
                  <button
                    onClick={() => navigator.clipboard.writeText(viewingMaterials.cover_letter_text)}
                    className="btn-secondary text-sm"
                  >
                    Copy Cover Letter
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function StatMini({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="bg-white border rounded-lg p-3 text-center">
      <p className="text-xs text-gray-500">{label}</p>
      <p className="text-xl font-bold">{value}</p>
    </div>
  );
}
