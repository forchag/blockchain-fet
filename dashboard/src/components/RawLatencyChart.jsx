import { useEffect, useMemo, useState } from 'react';

const W = 480;
const H = 220;
const PAD = { top: 20, right: 20, bottom: 44, left: 62 };
const CW = W - PAD.left - PAD.right;
const CH = H - PAD.top - PAD.bottom;
const GROUP_W = 0.7;

function mean(arr) {
  return arr.length ? arr.reduce((s, v) => s + v, 0) / arr.length : 0;
}

function useLatencyByPeer(rows) {
  return useMemo(() => {
    if (!rows.length) return { groups: [], yMax: 1500 };

    const byPeer = {};
    rows.forEach((r) => {
      if (r.peer_count == null) return;
      const p = r.peer_count;
      if (!byPeer[p]) byPeer[p] = { latencies: [], overheads: [] };
      byPeer[p].latencies.push(r.latency_ms);
      if (r.rbac_overhead_ms != null) byPeer[p].overheads.push(r.rbac_overhead_ms);
    });

    const peers = Object.keys(byPeer).map(Number).sort((a, b) => a - b);
    const groups = peers.map((p) => ({
      peer: p,
      total: mean(byPeer[p].latencies),
      overhead: mean(byPeer[p].overheads),
    }));

    const yMax = Math.ceil(Math.max(...groups.map((g) => g.total)) * 1.1);
    return { groups, yMax };
  }, [rows]);
}

function RawLatencyChart({ apiFetch }) {
  const [rows, setRows] = useState([]);
  const [error, setError] = useState('');

  useEffect(() => {
    apiFetch('/api/raw/latency')
      .then((d) => { setRows(d.rows); setError(''); })
      .catch((err) => setError(err.message));
  }, [apiFetch]);

  const { groups, yMax } = useLatencyByPeer(rows);

  const barW = groups.length ? (CW / groups.length) * GROUP_W : 60;
  const xCenter = (i) => PAD.left + (i + 0.5) * (CW / (groups.length || 1));
  const yScale = (v) => PAD.top + CH - (v / yMax) * CH;
  const barH = (v) => (v / yMax) * CH;

  const yTicks = 5;

  if (error) {
    return <p className="rounded-xl bg-red-900/40 p-4 text-sm text-red-300">{error}</p>;
  }

  return (
    <div>
      <h3 className="mb-3 text-lg font-semibold text-white">Latency distribution by peer count</h3>
      <div className="overflow-x-auto">
        <svg viewBox={`0 0 ${W} ${H}`} className="w-full min-w-[280px]" aria-label="Latency by peer count bar chart">
          {/* Y grid */}
          {Array.from({ length: yTicks + 1 }, (_, i) => {
            const val = (yMax / yTicks) * i;
            const cy = yScale(val);
            return (
              <g key={i}>
                <line x1={PAD.left} y1={cy} x2={PAD.left + CW} y2={cy} stroke="#334155" strokeWidth="1" />
                <text x={PAD.left - 6} y={cy + 4} textAnchor="end" fontSize="10" fill="#94a3b8">{Math.round(val)}</text>
              </g>
            );
          })}
          {/* Bars */}
          {groups.map((g, i) => {
            const cx = xCenter(i);
            const totalH = barH(g.total);
            const overH = barH(g.overhead);
            return (
              <g key={g.peer}>
                {/* Total latency bar (slate) */}
                <rect
                  x={cx - barW / 2}
                  y={yScale(g.total)}
                  width={barW}
                  height={totalH}
                  fill="#475569"
                  rx="2"
                />
                {/* RBAC overhead portion (cyan) */}
                <rect
                  x={cx - barW / 2}
                  y={yScale(g.overhead)}
                  width={barW}
                  height={overH}
                  fill="#0891b2"
                  rx="2"
                />
                <text x={cx} y={PAD.top + CH + 18} textAnchor="middle" fontSize="10" fill="#94a3b8">{g.peer} peers</text>
              </g>
            );
          })}
          {/* Axis labels */}
          <text x={PAD.left + CW / 2} y={H - 4} textAnchor="middle" fontSize="11" fill="#64748b">Peer count</text>
          <text x={14} y={PAD.top + CH / 2} textAnchor="middle" fontSize="11" fill="#64748b" transform={`rotate(-90, 14, ${PAD.top + CH / 2})`}>Latency (ms)</text>
          {/* Legend */}
          <rect x={PAD.left} y={PAD.top + 4} width="10" height="10" fill="#475569" rx="1" />
          <text x={PAD.left + 14} y={PAD.top + 13} fontSize="10" fill="#e2e8f0">Total latency</text>
          <rect x={PAD.left + 90} y={PAD.top + 4} width="10" height="10" fill="#0891b2" rx="1" />
          <text x={PAD.left + 104} y={PAD.top + 13} fontSize="10" fill="#e2e8f0">RBAC overhead</text>
        </svg>
      </div>
    </div>
  );
}

export default RawLatencyChart;
