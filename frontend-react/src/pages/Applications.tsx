import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api/client';
import { useAuth } from '../context/AuthContext';
import { MaterialsModal } from '../components/MaterialsModal';
import type { Application, ApplicationStats } from '../types';

interface ViewingMaterials {
  application_id: number;
  job_title: string;
  company: string;
}

export function Applications() {
  const { profileId } = useAuth();
  const [applications, setApplications] = useState<Application[]>([]);
  const [stats, setStats] = useState<ApplicationStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [viewingMaterials, setViewingMaterials] = useState<ViewingMaterials | null>(null);
  const [loadingMaterials, setLoadingMaterials] = useState<number | null>(null);

  useEffect(() => {
    if (!profileId) {
      setLoading(false);
      return;
    }
    Promise.all([api.applications.list(profileId), api.applications.getStats(profileId)])
      .then(([appsRes, statsRes]) => {
        setApplications(appsRes.data);
        setStats(statsRes.data);
      })
      .catch((err) => {
        console.error('Failed to load applications:', err);
      })
      .finally(() => setLoading(false));
  }, [profileId]);

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

  const handleViewMaterials = async (app: Application) => {
    setLoadingMaterials(app.application_id);
    try {
      // Verify materials exist before opening modal
      await api.applications.getMaterials(app.application_id);
      setViewingMaterials({
        application_id: app.application_id,
        job_title: app.job?.title || 'Unknown Job',
        company: app.job?.company || '',
      });
    } catch {
      alert('No materials found for this application');
    } finally {
      setLoadingMaterials(null);
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
      <h1 className="text-2xl font-bold text-white">Applications</h1>

      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
          <StatMini label="Applied" value={stats.total_applied} color="blue" />
          <StatMini label="Interviews" value={stats.interview_count} color="green" />
          <StatMini label="Rejected" value={stats.rejection_count} color="red" />
          <StatMini label="Offers" value={stats.offer_count} color="purple" />
          <StatMini label="Interview Rate" value={`${stats.interview_rate}%`} color="amber" />
        </div>
      )}

      {applications.length === 0 ? (
        <div className="card text-center py-12">
          <p className="text-slate-400 mb-4">No applications tracked yet.</p>
          <Link to="/jobs" className="btn-primary">Browse Jobs</Link>
        </div>
      ) : (
        <div className="space-y-3">
          {applications.map((app) => (
            <div key={app.application_id} className="card">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <h3 className="font-semibold text-white text-sm">{app.job?.title || 'Unknown Job'}</h3>
                  <p className="text-slate-400 text-xs">{app.job?.company || ''} {app.job?.location ? `• ${app.job.location}` : ''}</p>
                  <div className="flex items-center gap-4 mt-2 text-[11px] text-slate-500 font-mono">
                    <span>Applied: {new Date(app.date_applied).toLocaleDateString()}</span>
                    <span>Updated: {new Date(app.last_updated).toLocaleDateString()}</span>
                  </div>
                  {app.feedback_notes && (
                    <p className="mt-2 text-xs text-slate-500 italic">"{app.feedback_notes}"</p>
                  )}
                </div>
                <div className="flex items-center gap-3">
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => handleViewMaterials(app)}
                      disabled={loadingMaterials === app.application_id}
                      className="text-xs text-blue-400 hover:text-blue-300 disabled:opacity-50 transition-colors"
                    >
                      {loadingMaterials === app.application_id ? 'Loading...' : 'View / Edit'}
                    </button>
                    <span className="text-[#1E2D4A]">|</span>
                    <a
                      href={api.applications.downloadResumeHtml(app.application_id)}
                      download
                      className="text-xs text-slate-500 hover:text-slate-300 transition-colors"
                    >
                      Resume
                    </a>
                    <a
                      href={api.applications.downloadCoverLetterHtml(app.application_id)}
                      download
                      className="text-xs text-slate-500 hover:text-slate-300 transition-colors"
                    >
                      Cover Letter
                    </a>
                  </div>
                  <select
                    value={app.status}
                    onChange={(e) => handleStatusUpdate(app.application_id, e.target.value)}
                    className="input-field text-xs py-1 px-2 w-auto"
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

      {/* Materials Modal */}
      <MaterialsModal
        isOpen={!!viewingMaterials}
        onClose={() => setViewingMaterials(null)}
        applicationId={viewingMaterials?.application_id || null}
        jobTitle={viewingMaterials?.job_title || ''}
        company={viewingMaterials?.company || ''}
      />
    </div>
  );
}

function StatMini({ label, value, color }: { label: string; value: string | number; color: string }) {
  const colorMap: Record<string, string> = {
    blue: 'text-blue-400',
    green: 'text-emerald-400',
    red: 'text-red-400',
    purple: 'text-purple-400',
    amber: 'text-amber-400',
  };
  return (
    <div className="rounded-lg border border-[#1E2D4A] bg-[#0E1628] p-3 text-center">
      <p className="text-[10px] text-slate-500 uppercase tracking-wider">{label}</p>
      <p className={`text-xl font-bold mt-1 ${colorMap[color] || 'text-slate-200'}`}>{value}</p>
    </div>
  );
}
