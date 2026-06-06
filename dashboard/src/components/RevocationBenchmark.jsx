import paperBenchmarks from '../data/paperBenchmarks.js';

const { revocation } = paperBenchmarks;

const revocationMetrics = [
  { label: 'CRL publication time', value: `${revocation.crl_publication_time_seconds} seconds` },
  { label: 'CRL gossip propagation', value: `${revocation.crl_gossip_propagation_minutes} minutes average` },
  { label: 'CRL schedule', value: `${revocation.crl_schedule_hours} hours` },
  { label: 'Policy cache TTL', value: `${revocation.policy_cache_ttl_seconds} seconds` },
  { label: 'Nonce retention window', value: `${revocation.nonce_retention_days} days` },
];

function RevocationBenchmark() {
  return (
    <section className="rounded-2xl border border-slate-700 bg-slate-800/60 p-4">
      <div className="mb-4">
        <h3 className="text-lg font-semibold text-white">Revocation benchmark</h3>
        <p className="text-xs font-semibold uppercase tracking-wide text-cyan-300">Paper-reported benchmark results</p>
      </div>
      <dl className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
        {revocationMetrics.map((metric) => (
          <div key={metric.label} className="rounded-xl bg-slate-950/60 p-3">
            <dt className="text-xs uppercase tracking-wide text-slate-500">{metric.label}</dt>
            <dd className="mt-1 text-xl font-bold text-white">{metric.value}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}

export default RevocationBenchmark;
