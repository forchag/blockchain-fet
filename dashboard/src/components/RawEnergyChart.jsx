import { useEffect, useMemo, useState } from 'react';

const W = 340;
const H = 200;
const PAD = { top: 20, right: 24, bottom: 44, left: 58 };
const CW = W - PAD.left - PAD.right;
const CH = H - PAD.top - PAD.bottom;
const BAR_W = 60;

const MODES = [
  { key: 'SingleChannel', label: 'Single Channel', color: '#475569' },
  { key: 'CRT', label: 'CRT', color: '#22d3ee' },
];

function mean(arr) {
  return arr.length ? arr.reduce((s, v) => s + v, 0) / arr.length : 0;
}

function useEnergyMeans(rows) {
  return useMemo(() => {
    const sc = rows.filter((r) => r.mode === 'SingleChannel').map((r) => r.energy_mj);
    const crt = rows.filter((r) => r.mode === 'CRT').map((r) => r.energy_mj);
    return { SingleChannel: mean(sc), CRT: mean(crt) };
  }, [rows]);
}

function RawEnergyChart({ apiFetch }) {
  const [rows, setRows] = useState([]);
  const [error, setError] = useState('');

  useEffect(() => {
    apiFetch('/api/raw/energy')
      .then((d) => { setRows(d.rows); setError(''); })
      .catch((err) => setError(err.message));
  }, [apiFetch]);

  const means = useEnergyMeans(rows);
  const yMax = Math.ceil(Math.max(...Object.values(means)) * 1.15);
  const yScale = (v) => PAD.top + CH - (v / yMax) * CH;
  const barH = (v) => (v / yMax) * CH;

  const spacing = CW / (MODES.length + 1);

  const yTicks = 4;

  if (error) {
    return <p className="rounded-xl bg-red-900/40 p-4 text-sm text-red-300">{error}</p>;
  }

  return (
    <div>
      <h3 className="mb-3 text-lg font-semibold text-white">Energy per transmission</h3>
      <div className="overflow-x-auto">
        <svg viewBox={`0 0 ${W} ${H}`} className="w-full min-w-[240px]" aria-label="Energy comparison bar chart">
          {/* Y grid */}
          {Array.from({ length: yTicks + 1 }, (_, i) => {
            const val = (yMax / yTicks) * i;
            const cy = yScale(val);
            return (
              <g key={i}>
                <line x1={PAD.left} y1={cy} x2={PAD.left + CW} y2={cy} stroke="#334155" strokeWidth="1" />
                <text x={PAD.left - 6} y={cy + 4} textAnchor="end" fontSize="10" fill="#94a3b8">{val.toFixed(1)}</text>
              </g>
            );
          })}
          {/* Bars */}
          {MODES.map(({ key, label, color }, i) => {
            const cx = PAD.left + spacing * (i + 1);
            const val = means[key] || 0;
            return (
              <g key={key}>
                <rect x={cx - BAR_W / 2} y={yScale(val)} width={BAR_W} height={barH(val)} fill={color} rx="3" />
                <text x={cx} y={yScale(val) - 4} textAnchor="middle" fontSize="10" fill="#e2e8f0">{val.toFixed(2)}</text>
                <text x={cx} y={PAD.top + CH + 16} textAnchor="middle" fontSize="10" fill="#94a3b8">{label}</text>
              </g>
            );
          })}
          {/* Y axis label */}
          <text x={14} y={PAD.top + CH / 2} textAnchor="middle" fontSize="11" fill="#64748b" transform={`rotate(-90, 14, ${PAD.top + CH / 2})`}>Energy (mJ)</text>
          <text x={PAD.left + CW / 2} y={H - 4} textAnchor="middle" fontSize="11" fill="#64748b">LoRa transmission mode</text>
        </svg>
      </div>
    </div>
  );
}

export default RawEnergyChart;
