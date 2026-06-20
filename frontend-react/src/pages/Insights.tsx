import { useState, useEffect } from 'react';
import { api } from '../api/client';
import { CheckCircle, XCircle, Lightbulb, Info } from 'lucide-react';

const PROFILE_ID_KEY = 'career_agent_profile_id';

interface Insights {
  rejection_patterns: string[];
  success_patterns: string[];
  improvement_suggestions: string[];
  interview_conversion_rate: number;
  insights: string[];
}

export function Insights() {
  const [insights, setInsights] = useState<Insights | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const stored = localStorage.getItem(PROFILE_ID_KEY);
    const profileId = stored ? Number(stored) : 1;
    api.applications.getInsights(profileId)
      .then((res) => setInsights(res.data))
      .catch((err) => {
        setError(err.response?.data?.detail || 'Failed to load insights');
      })
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-bold text-white">Career Insights</h1>
        <div className="card text-center py-12">
          <p className="text-red-400">{error}</p>
        </div>
      </div>
    );
  }

  if (!insights) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-bold text-white">Career Insights</h1>
        <div className="card text-center py-12">
          <p className="text-slate-500">No insights available. Upload a resume and apply to jobs to generate insights.</p>
        </div>
      </div>
    );
  }

  const convRate = insights.interview_conversion_rate ?? 0;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-white">Career Insights</h1>

      {/* Conversion Rate */}
      <div className="card">
        <h2 className="text-sm font-semibold text-white mb-3">Interview Conversion Rate</h2>
        <div className="flex items-center gap-4">
          <div className="text-4xl font-bold text-blue-400">{(convRate * 100).toFixed(0)}%</div>
          <p className="text-xs text-slate-500">
            {convRate === 0 ? 'Insufficient data to calculate' : 'Of applications lead to interviews'}
          </p>
        </div>
      </div>

      {/* Insight Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <InsightCard
          title="Success Patterns"
          items={insights.success_patterns}
          icon={CheckCircle}
          color="green"
        />
        <InsightCard
          title="Rejection Patterns"
          items={insights.rejection_patterns}
          icon={XCircle}
          color="red"
        />
        <InsightCard
          title="Improvement Suggestions"
          items={insights.improvement_suggestions}
          icon={Lightbulb}
          color="blue"
        />
        <InsightCard
          title="Key Insights"
          items={insights.insights}
          icon={Info}
          color="amber"
        />
      </div>
    </div>
  );
}

function InsightCard({ title, items, icon: Icon, color }: {
  title: string;
  items: string[];
  icon: any;
  color: string;
}) {
  const colorMap: Record<string, { border: string; iconColor: string; bg: string }> = {
    blue: { border: 'border-blue-500/20', iconColor: 'text-blue-400', bg: 'bg-blue-500/5' },
    green: { border: 'border-emerald-500/20', iconColor: 'text-emerald-400', bg: 'bg-emerald-500/5' },
    amber: { border: 'border-amber-500/20', iconColor: 'text-amber-400', bg: 'bg-amber-500/5' },
    red: { border: 'border-red-500/20', iconColor: 'text-red-400', bg: 'bg-red-500/5' },
  };
  const c = colorMap[color] || colorMap.blue;

  return (
    <div className={`rounded-xl border ${c.border} ${c.bg} p-5`}>
      <div className="flex items-center gap-2 mb-4">
        <Icon className={`w-5 h-5 ${c.iconColor}`} />
        <h2 className="text-sm font-semibold text-white">{title}</h2>
      </div>
      {items.length === 0 ? (
        <p className="text-slate-500 text-xs">No data available</p>
      ) : (
        <ul className="space-y-2">
          {items.map((item, i) => (
            <li key={i} className="text-xs text-slate-300 flex items-start gap-2">
              <span className="text-slate-600 mt-0.5">•</span>
              {item}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
