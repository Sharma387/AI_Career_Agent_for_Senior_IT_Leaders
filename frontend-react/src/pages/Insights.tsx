import { useState, useEffect } from 'react';
import { api } from '../api/client';

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
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-8">
        <h1 className="text-2xl font-bold">Career Insights</h1>
        <div className="card text-center py-12">
          <p className="text-red-500">{error}</p>
        </div>
      </div>
    );
  }

  if (!insights) {
    return (
      <div className="space-y-8">
        <h1 className="text-2xl font-bold">Career Insights</h1>
        <div className="card text-center py-12">
          <p className="text-gray-500">No insights available. Upload a resume and apply to jobs to generate insights.</p>
        </div>
      </div>
    );
  }

  const convRate = insights.interview_conversion_rate ?? 0;

  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-bold">Career Insights</h1>

      <div className="card">
        <h2 className="text-lg font-semibold mb-2">Interview Conversion Rate</h2>
        <div className="flex items-center gap-4">
          <div className="text-4xl font-bold text-blue-600">{(convRate * 100).toFixed(0)}%</div>
          <p className="text-sm text-gray-500">
            {convRate === 0 ? 'Insufficient data to calculate' : 'Of applications lead to interviews'}
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <InsightCard
          title="Success Patterns"
          items={insights.success_patterns}
          color="green"
          icon="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
        />
        <InsightCard
          title="Rejection Patterns"
          items={insights.rejection_patterns}
          color="red"
          icon="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z"
        />
        <InsightCard
          title="Improvement Suggestions"
          items={insights.improvement_suggestions}
          color="blue"
          icon="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
        />
        <InsightCard
          title="Key Insights"
          items={insights.insights}
          color="amber"
          icon="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
        />
      </div>
    </div>
  );
}

function InsightCard({ title, items, color, icon }: {
  title: string;
  items: string[];
  color: string;
  icon: string;
}) {
  const colorMap: Record<string, { bg: string; border: string; icon: string }> = {
    blue: { bg: 'bg-blue-50', border: 'border-blue-200', icon: 'text-blue-600' },
    green: { bg: 'bg-green-50', border: 'border-green-200', icon: 'text-green-600' },
    amber: { bg: 'bg-amber-50', border: 'border-amber-200', icon: 'text-amber-600' },
    red: { bg: 'bg-red-50', border: 'border-red-200', icon: 'text-red-600' },
  };
  const c = colorMap[color] || colorMap.blue;

  return (
    <div className={`rounded-xl border ${c.border} ${c.bg} p-6`}>
      <div className="flex items-center gap-3 mb-4">
        <svg className={`w-6 h-6 ${c.icon}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d={icon} />
        </svg>
        <h2 className="text-lg font-semibold">{title}</h2>
      </div>
      {items.length === 0 ? (
        <p className="text-gray-500 text-sm">No data available</p>
      ) : (
        <ul className="space-y-2">
          {items.map((item, i) => (
            <li key={i} className="text-sm text-gray-700 flex items-start gap-2">
              <span className="text-gray-400 mt-0.5">•</span>
              {item}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
