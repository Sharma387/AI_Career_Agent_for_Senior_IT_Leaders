import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { api } from '../api/client';
import type { ApplicationStats, Application } from '../types';

export function Dashboard() {
  const { user, profileId } = useAuth();
  const [stats, setStats] = useState<ApplicationStats | null>(null);
  const [recentApps, setRecentApps] = useState<Application[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!profileId) {
      setLoading(false);
      return;
    }
    const loadDashboard = async () => {
      try {
        const [statsRes, appsRes] = await Promise.all([
          api.applications.getStats(profileId),
          api.applications.list(profileId),
        ]);
        setStats(statsRes.data);
        setRecentApps(appsRes.data.slice(0, 5));
      } catch {
        // Dashboard data unavailable
      } finally {
        setLoading(false);
      }
    };
    loadDashboard();
  }, [profileId]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">
          Welcome back, {user?.full_name || user?.email}
        </h1>
        <p className="text-gray-600 mt-1">Here's your career progress overview</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <StatCard label="Applications" value={stats?.total_applied || 0} color="blue" />
        <StatCard label="Interviews" value={stats?.interview_count || 0} color="green" />
        <StatCard label="Offers" value={stats?.offer_count || 0} color="purple" />
        <StatCard label="Success Rate" value={`${stats?.success_rate || 0}%`} color="amber" />
      </div>

      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold">Recent Applications</h2>
          <Link to="/applications" className="text-sm text-blue-600 hover:text-blue-700">
            View all
          </Link>
        </div>

        {recentApps.length === 0 ? (
          <p className="text-gray-500 text-center py-8">
            No applications yet. Start by browsing{' '}
            <Link to="/jobs" className="text-blue-600 hover:underline">jobs</Link>.
          </p>
        ) : (
          <div className="space-y-3">
            {recentApps.map((app) => (
              <div key={app.application_id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                <div>
                  <p className="font-medium">{app.job.title}</p>
                  <p className="text-sm text-gray-500">{app.job.company}</p>
                </div>
                <StatusBadge status={app.status} />
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Link to="/profile" className="card hover:shadow-md transition-shadow group">
          <h3 className="font-semibold group-hover:text-blue-600 transition-colors">Complete Your Profile</h3>
          <p className="text-sm text-gray-500 mt-1">Upload your resume and add projects to improve matches</p>
        </Link>
        <Link to="/jobs" className="card hover:shadow-md transition-shadow group">
          <h3 className="font-semibold group-hover:text-blue-600 transition-colors">Browse Jobs</h3>
          <p className="text-sm text-gray-500 mt-1">Find senior IT leadership roles matching your experience</p>
        </Link>
      </div>
    </div>
  );
}

function StatCard({ label, value, color }: { label: string; value: string | number; color: string }) {
  const colorMap: Record<string, string> = {
    blue: 'bg-blue-50 text-blue-700',
    green: 'bg-green-50 text-green-700',
    purple: 'bg-purple-50 text-purple-700',
    amber: 'bg-amber-50 text-amber-700',
  };
  return (
    <div className={`rounded-xl p-6 ${colorMap[color] || 'bg-gray-50 text-gray-700'}`}>
      <p className="text-sm font-medium opacity-75">{label}</p>
      <p className="text-3xl font-bold mt-1">{value}</p>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    applied: 'bg-blue-100 text-blue-700',
    interview: 'bg-green-100 text-green-700',
    offer: 'bg-purple-100 text-purple-700',
    rejected: 'bg-red-100 text-red-700',
    withdrawn: 'bg-gray-100 text-gray-700',
  };
  return (
    <span className={`px-3 py-1 rounded-full text-xs font-medium ${styles[status] || 'bg-gray-100 text-gray-700'}`}>
      {status.charAt(0).toUpperCase() + status.slice(1)}
    </span>
  );
}
