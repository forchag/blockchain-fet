import paperBenchmarks from '../data/paperBenchmarks.js';

const { security } = paperBenchmarks;

const securityMetrics = [
  { label: 'Security attempts', value: security.security_test_attempts.toLocaleString() },
  { label: 'Vectors', value: security.security_vectors.toLocaleString() },
  { label: 'Attempts per vector', value: security.attempts_per_vector.toLocaleString() },
  { label: 'Block rate', value: `${security.block_rate_percent}%` },
  { label: 'Blocked attempts on day 34', value: security.day_34_blocked_attempts.toLocaleString() },
];

function SecurityBenchmark() {
  return (
    <section className="rounded-2xl border border-slate-700 bg-slate-800/60 p-4">
      <div className="mb-4">
        <h3 className="text-lg font-semibold text-white">Security benchmark</h3>
        <p className="text-xs font-semibold uppercase tracking-wide text-cyan-300">Paper-reported benchmark results</p>
      </div>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
        {securityMetrics.map((metric) => (
          <div key={metric.label} className="rounded-xl bg-slate-950/60 p-3">
            <p className="text-xs uppercase tracking-wide text-slate-500">{metric.label}</p>
            <p className="mt-1 text-2xl font-bold text-white">{metric.value}</p>
          </div>
        ))}
      </div>
    </section>
  );
}

export default SecurityBenchmark;
