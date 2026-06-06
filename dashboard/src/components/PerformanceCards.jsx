import paperBenchmarks from '../data/paperBenchmarks.js';

const { deployment, latency, throughput, transactions } = paperBenchmarks;

const cards = [
  {
    label: `HRBAC TPS at ${throughput.concurrent_clients} clients`,
    value: throughput.hrbac_tps.toLocaleString(),
    detail: 'Throughput with hierarchical role-based access control enabled.',
  },
  {
    label: `Baseline TPS at ${throughput.concurrent_clients} clients`,
    value: throughput.baseline_tps.toLocaleString(),
    detail: 'Reference throughput reported for the same client count.',
  },
  {
    label: 'RBAC overhead',
    value: `${throughput.rbac_overhead_percent}%`,
    detail: 'Reported throughput overhead compared with the baseline.',
  },
  {
    label: 'Total sensor-write latency',
    value: `${latency.sensor_write_total_latency_ms.toLocaleString()}ms`,
    detail: 'End-to-end latency for a sensor-write transaction.',
  },
  {
    label: 'RBAC overhead on sensor write',
    value: `${latency.rbac_overhead_sensor_write_ms.toLocaleString()}ms`,
    detail: 'Access-control portion of the sensor-write path.',
  },
  {
    label: 'Peak observed TPS',
    value: transactions.peak_observed_tps.toLocaleString(),
    detail: 'Highest observed transaction throughput in the deployment.',
  },
  {
    label: 'System uptime',
    value: `${deployment.system_uptime_percent}%`,
    detail: 'Reported uptime across the field deployment.',
  },
];

function PerformanceCards() {
  return (
    <section>
      <div className="mb-3 flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
        <h3 className="text-lg font-semibold text-white">Performance and availability</h3>
        <span className="text-xs font-semibold uppercase tracking-wide text-cyan-300">Paper-reported benchmark results</span>
      </div>
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {cards.map((card) => (
          <article key={card.label} className="rounded-2xl border border-slate-700 bg-slate-800/70 p-4">
            <p className="text-sm text-slate-400">{card.label}</p>
            <p className="mt-2 text-3xl font-bold text-white">{card.value}</p>
            <p className="mt-2 text-sm text-slate-300">{card.detail}</p>
          </article>
        ))}
      </div>
    </section>
  );
}

export default PerformanceCards;
