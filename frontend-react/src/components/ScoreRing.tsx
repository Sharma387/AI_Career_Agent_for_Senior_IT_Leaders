interface ScoreRingProps {
  score: number;
  size?: number;
  loading?: boolean;
}

export function ScoreRing({ score, size = 160, loading = false }: ScoreRingProps) {
  const r = (size - 12) / 2;
  const c = 2 * Math.PI * r;
  const fill = (score / 100) * c;
  const color = score >= 75 ? '#10B981' : score >= 50 ? '#F59E0B' : '#EF4444';
  const fontSize = size * 0.22;
  const labelSize = size * 0.07;

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center gap-2" style={{ width: size, height: size }}>
        <div className="animate-spin rounded-full border-b-2 border-blue-500" style={{ width: size * 0.3, height: size * 0.3 }} />
        <span className="text-[10px] text-slate-500 uppercase tracking-wider">Analyzing...</span>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center">
      <div className="relative flex items-center justify-center" style={{ width: size, height: size }}>
        <svg viewBox={`0 0 ${size} ${size}`} width={size} height={size} className="rotate-[-90deg]">
          <circle
            cx={size / 2}
            cy={size / 2}
            r={r}
            fill="none"
            stroke="#1E2D4A"
            strokeWidth="6"
          />
          <circle
            cx={size / 2}
            cy={size / 2}
            r={r}
            fill="none"
            stroke={color}
            strokeWidth="6"
            strokeDasharray={c}
            strokeDashoffset={c - fill}
            strokeLinecap="round"
            style={{ transition: 'stroke-dashoffset 1s ease' }}
          />
        </svg>
        <div className="absolute flex flex-col items-center">
          <span className="font-bold font-mono" style={{ fontSize, color }}>
            {score}
          </span>
          <span className="text-slate-500 uppercase tracking-widest font-semibold" style={{ fontSize: labelSize }}>
            Match Score
          </span>
        </div>
      </div>
    </div>
  );
}
