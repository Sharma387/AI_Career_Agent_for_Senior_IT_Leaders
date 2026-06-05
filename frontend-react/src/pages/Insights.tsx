import { useState, useEffect } from 'react';
import { api } from '../api/client';

interface Insights {
  recommendations: string[];
  market_trends: string[];
  skill_gaps: string[];
}

export function Insights() {
  const [insights, setInsights] = useState<Insights | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.insights.get()
      .then((res) => setInsights(res.data))
      .catch(() => null)
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
      </div>
    );
  }

  if (!insights) {
    return (
      <div className="space-y-8">
        <h1 className="text-2xl font-bold">Career Insights</h1>
        <div className="card text-center py-12">
          <p className="text-gray-500">No insights available. Complete your profile to generate insights.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-bold">Career Insights</h1>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <InsightCard
          title="Recommendations"
          items={insights.recommendations}
          color="blue"
          icon="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4"
        />
        <InsightCard
          title="Market Trends"
          items={insights.market_trends}
          color="green"
          icon="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"
        />
        <InsightCard
          title="Skill Gaps"
          items={insights.skill_gaps}
          color="amber"
          icon="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
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
