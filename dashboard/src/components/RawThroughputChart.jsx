import { useEffect, useMemo, useState } from 'react';

const W = 560;
const H = 220;
const PAD = { top: 20, right: 24, bottom: 44, left: 52 };
const CW = W - PAD.left - PAD.right;
const CH = H - PAD.top - PAD.bottom;

function mean(arr) {
  return arr.length ? arr.reduce((s, v) => s + v, 0) / arr.length : 0;
}

function useSeries(rows) {
  return useMemo(() => {
    if (!rows.length) return { hrbac: [], baseline: [], clients: [], yMin: 0, yMax: 100 };

    const byKey = {};
    rows.forEach((r) => {
      const k = `${r.benchmark_type}:${r.concurrent_clients}`;
      (byKey[k] = byKey[k] || []).push(r.tps);
    });

    const clients = [...new Set(rows.map((r) => r.concurrent_clients))].sort((a, b) => a - b);
    const hrbac = clients.map((c) => ({ x: c, y: mean(byKey[`HRBAC:${c}`] || []) }));
    const baseline = clients.map((c) => ({ x: c, y: mean(byKey[`Baseline:${c}`] || []) }));

    const allY = [...hrbac, ...baseline].map((p) => p.y);
    const yMin = Math.floor(Math.min(...allY) * 0.9);
    const yMax = Math.ceil(Math.max(...allY) * 1.05);

    return { hrbac, baseline, clients, yMin, yMax };
  }, [rows]);
}

function toPath(points, xScale, yScale) {
  return points.map(({ x, y }) => `${xScale(x).toFixed(1)},${yScale(y).toFixed(1)}`).join(' ');
}

function RawThroughputChart({ apiFetch }) {
  const [rows, setRows] = useState([]);
  const [error, setError] = useState('');

  useEffect(() => {
    apiFetch('/api/raw/throughput')
      .then((d) => { setRows(d.rows); setError(''); })
      .catch((err) => setError(err.message));
  }, [apiFetch]);

  const { hrbac, baseline, clients, yMin, yMax } = useSeries(rows);

  const xScale = (v) => PAD.left + ((v - clients[0]) / (clients[clients.length - 1] - clients[0])) * CW;
  const yScale = (v) => PAD.top + CH - ((v - yMin) / (yMax - yMin)) * CH;

  const yTicks = 5;
  const yStep = (yMax - yMin) / yTicks;

  if (error) {
    return <p className="rounded-xl bg-red-900/40 p-4 text-sm text-red-300">{error}</p>;
  }

  return (
    <div>
      <h3 className="mb-3 text-lg font-semibold text-white">Throughput vs concurrent clients</h3>
      <div className="overflow-x-auto">
        <svg viewBox={`0 0 ${W} ${H}`} className="w-full min-w-[320px]" aria-label="TPS vs concurrent clients line chart">
          {/* Y grid + ticks */}
          {Array.from({ length: yTicks + 1 }, (_, i) => {
            const val = yMin + i * yStep;
            const cy = yScale(val);
            return (
              <g key={i}>
                <line x1={PAD.left} y1={cy} x2={PAD.left + CW} y2={cy} stroke="#334155" strokeWidth="1" />
                <text x={PAD.left - 6} y={cy + 4} textAnchor="end" fontSize="10" fill="#94a3b8">{Math.round(val)}</text>
              </g>
            );
          })}
          {/* X ticks */}
          {clients.map((c) => (
            <text key={c} x={xScale(c)} y={PAD.top + CH + 18} textAnchor="middle" fontSize="10" fill="#94a3b8">{c}</text>
          ))}
          {/* Axis labels */}
          <text x={PAD.left + CW / 2} y={H - 4} textAnchor="middle" fontSize="11" fill="#64748b">Concurrent clients</text>
          <text x={14} y={PAD.top + CH / 2} textAnchor="middle" fontSize="11" fill="#64748b" transform={`rotate(-90, 14, ${PAD.top + CH / 2})`}>TPS</text>
          {/* Lines */}
          {rows.length > 0 && (
            <>
              <polyline points={toPath(baseline, xScale, yScale)} fill="none" stroke="#64748b" strokeWidth="2" strokeLinejoin="round" />
              <polyline points={toPath(hrbac, xScale, yScale)} fill="none" stroke="#22d3ee" strokeWidth="2.5" strokeLinejoin="round" />
              {hrbac.map(({ x, y }) => (
                <circle key={x} cx={xScale(x)} cy={yScale(y)} r="3" fill="#22d3ee" />
              ))}
              {baseline.map(({ x, y }) => (
                <circle key={x} cx={xScale(x)} cy={yScale(y)} r="3" fill="#64748b" />
              ))}
            </>
          )}
          {/* Legend */}
          <circle cx={PAD.left + 8} cy={PAD.top + 4} r="4" fill="#22d3ee" />
          <text x={PAD.left + 16} y={PAD.top + 8} fontSize="10" fill="#e2e8f0">HRBAC</text>
          <circle cx={PAD.left + 72} cy={PAD.top + 4} r="4" fill="#64748b" />
          <text x={PAD.left + 80} y={PAD.top + 8} fontSize="10" fill="#e2e8f0">Baseline</text>
        </svg>
      </div>
    </div>
  );
}

export default RawThroughputChart;
