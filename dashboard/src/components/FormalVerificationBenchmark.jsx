import paperBenchmarks from '../data/paperBenchmarks.js';

const { formal_verification: formalVerification } = paperBenchmarks;

const verificationMetrics = [
  { label: 'TLA+ states explored', value: formalVerification.tla_states_explored.toLocaleString() },
  { label: 'Model diameter', value: formalVerification.tla_model_diameter.toLocaleString() },
  { label: 'Runtime', value: `${formalVerification.tla_runtime_seconds} seconds` },
  { label: 'CPU', value: formalVerification.tla_cpu },
];

function FormalVerificationBenchmark() {
  return (
    <section className="rounded-2xl border border-violet-300/20 bg-violet-400/10 p-4">
      <div className="mb-4">
        <h3 className="text-lg font-semibold text-white">Formal verification benchmark</h3>
        <p className="text-xs font-semibold uppercase tracking-wide text-violet-200">Paper-reported benchmark results</p>
      </div>
      <dl className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {verificationMetrics.map((metric) => (
          <div key={metric.label} className="rounded-xl bg-slate-950/60 p-3">
            <dt className="text-xs uppercase tracking-wide text-violet-100/70">{metric.label}</dt>
            <dd className="mt-1 text-2xl font-bold text-white">{metric.value}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}

export default FormalVerificationBenchmark;
