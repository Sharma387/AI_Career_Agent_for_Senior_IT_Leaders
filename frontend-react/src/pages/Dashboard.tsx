import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { api } from '../api/client';
import { Briefcase, MessageSquare, Trophy, TrendingUp, FileText, Search } from 'lucide-react';
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
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500" />
      </div>
    );
  }

  const firstName = user?.full_name?.split(' ')[0] || user?.email?.split('@')[0] || 'there';

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">
            Good morning, <span className="text-blue-400">{firstName}</span> 👋
          </h1>
          <p className="text-slate-500 mt-1 text-sm">Your career intelligence centre</p>
        </div>
        <Link to="/jobs" className="btn-primary">
          + Add Job
        </Link>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <StatCard
          icon={Briefcase}
          label="Applications"
          value={stats?.total_applied || 0}
          color="blue"
        />
        <StatCard
          icon={MessageSquare}
          label="Interviews"
          value={stats?.interview_count || 0}
          color="green"
        />
        <StatCard
          icon={Trophy}
          label="Offers"
          value={stats?.offer_count || 0}
          color="purple"
        />
        <StatCard
          icon={TrendingUp}
          label="Success Rate"
          value={`${stats?.success_rate || 0}%`}
          color="amber"
        />
      </div>

      {/* Recent Applications */}
      <div className="card">
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-base font-semibold text-white">Recent Applications</h2>
          <Link to="/applications" className="text-sm text-blue-400 hover:text-blue-300 transition-colors">
            View all →
          </Link>
        </div>

        {recentApps.length === 0 ? (
          <p className="text-slate-500 text-center py-8 text-sm">
            No applications yet. Start by browsing{' '}
            <Link to="/jobs" className="text-blue-400 hover:underline">jobs</Link>.
          </p>
        ) : (
          <div className="space-y-2">
            {recentApps.map((app) => (
              <div key={app.application_id} className="flex items-center justify-between p-3 bg-[#0E1628] rounded-lg border border-[#1E2D4A]">
                <div>
                  <p className="font-medium text-slate-200 text-sm">{app.job.title}</p>
                  <p className="text-xs text-slate-500">{app.job.company}</p>
                </div>
                <StatusBadge status={app.status} />
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Link to="/resume" className="card hover:border-blue-500/50 transition-colors group">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-blue-500/10 flex items-center justify-center">
              <FileText className="w-5 h-5 text-blue-400" />
            </div>
            <div>
              <h3 className="font-semibold text-white group-hover:text-blue-400 transition-colors text-sm">Complete Your Profile</h3>
              <p className="text-xs text-slate-500 mt-0.5">Upload your resume and add projects to improve matches</p>
            </div>
          </div>
        </Link>
        <Link to="/jobs" className="card hover:border-blue-500/50 transition-colors group">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-amber-500/10 flex items-center justify-center">
              <Search className="w-5 h-5 text-amber-400" />
            </div>
            <div>
              <h3 className="font-semibold text-white group-hover:text-blue-400 transition-colors text-sm">Browse Jobs</h3>
              <p className="text-xs text-slate-500 mt-0.5">Find senior IT leadership roles matching your experience</p>
            </div>
          </div>
        </Link>
      </div>
    </div>
  );
}

function StatCard({ icon: Icon, label, value, color }: { icon: any; label: string; value: string | number; color: string }) {
  const colorMap: Record<string, { iconBg: string; iconColor: string; valueColor: string }> = {
    blue: { iconBg: 'bg-blue-500/10', iconColor: 'text-blue-400', valueColor: 'text-blue-400' },
    green: { iconBg: 'bg-emerald-500/10', iconColor: 'text-emerald-400', valueColor: 'text-emerald-400' },
    purple: { iconBg: 'bg-purple-500/10', iconColor: 'text-purple-400', valueColor: 'text-purple-400' },
    amber: { iconBg: 'bg-amber-500/10', iconColor: 'text-amber-400', valueColor: 'text-amber-400' },
  };
  const c = colorMap[color] || colorMap.blue;

  return (
    <div className="rounded-xl border border-[#1E2D4A] bg-[#0E1628] p-5">
      <div className="flex items-center gap-3 mb-3">
        <div className={`w-9 h-9 rounded-lg ${c.iconBg} flex items-center justify-center`}>
          <Icon className={`w-4 h-4 ${c.iconColor}`} />
        </div>
      </div>
      <p className={`text-2xl font-bold ${c.valueColor}`}>{value}</p>
      <p className="text-xs text-slate-500 mt-1">{label}</p>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    applied: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
    interview: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
    offer: 'bg-purple-500/10 text-purple-400 border-purple-500/20',
    rejected: 'bg-red-500/10 text-red-400 border-red-500/20',
    withdrawn: 'bg-slate-500/10 text-slate-400 border-slate-500/20',
  };
  return (
    <span className={`px-2.5 py-1 rounded-full text-[11px] font-medium border ${styles[status] || styles.applied}`}>
      {status.charAt(0).toUpperCase() + status.slice(1)}
    </span>
  );
}
