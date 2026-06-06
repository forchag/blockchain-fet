import { useEffect, useState } from 'react';

const METRICS = [
  { key: 'sensor_transaction_count', label: 'Sensor transactions', fmt: (v) => v?.toLocaleString() },
  { key: 'security_attempt_count', label: 'Security attempts', fmt: (v) => v?.toLocaleString() },
  { key: 'mean_hrbac_tps_50_clients', label: 'Mean HRBAC TPS (50 clients)', fmt: (v) => v != null ? `${v} TPS` : '—' },
  { key: 'mean_baseline_tps_50_clients', label: 'Mean baseline TPS (50 clients)', fmt: (v) => v != null ? `${v} TPS` : '—' },
  { key: 'mean_sensor_write_latency_ms', label: 'Mean sensor-write latency', fmt: (v) => v != null ? `${v} ms` : '—' },
  { key: 'mean_rbac_overhead_ms', label: 'Mean RBAC overhead', fmt: (v) => v != null ? `${v} ms` : '—' },
  { key: 'energy_reduction_percent', label: 'Energy reduction (CRT vs single)', fmt: (v) => v != null ? `${v}%` : '—' },
  { key: 'uptime_percent', label: 'Uptime', fmt: (v) => v != null ? `${v}%` : '—' },
];

function RawDataOverview({ apiFetch }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    apiFetch('/api/raw/summary')
      .then((d) => { setData(d); setError(''); })
      .catch((err) => setError(err.message));
  }, [apiFetch]);

  if (error) {
    return (
      <p className="rounded-xl bg-red-900/40 p-4 text-sm text-red-300">{error}</p>
    );
  }

  return (
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
      {METRICS.map(({ key, label, fmt }) => (
        <article key={key} className="rounded-2xl border border-slate-700 bg-slate-800/70 p-4">
          <p className="text-sm text-slate-400">{label}</p>
          <p className="mt-2 text-2xl font-bold text-white">
            {data ? fmt(data[key]) : '…'}
          </p>
        </article>
      ))}
    </div>
  );
}

export default RawDataOverview;
