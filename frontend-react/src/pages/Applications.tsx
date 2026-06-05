import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api/client';
import type { Application, ApplicationStats } from '../types';

export function Applications() {
  const [applications, setApplications] = useState<Application[]>([]);
  const [stats, setStats] = useState<ApplicationStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([api.applications.list(), api.applications.getStats()])
      .then(([appsRes, statsRes]) => {
        setApplications(appsRes.data);
        setStats(statsRes.data);
      })
      .catch(() => null)
      .finally(() => setLoading(false));
  }, []);

  const handleStatusUpdate = async (appId: string, newStatus: string) => {
    try {
      await api.applications.updateStatus(appId, newStatus);
      setApplications(applications.map((app: Application) =>
        app.application_id === appId ? { ...app, status: newStatus, last_updated: new Date().toISOString() } : app
      ));
    } catch {
      alert('Failed to update status');
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
                <div>
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
