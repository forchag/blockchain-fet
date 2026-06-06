import paperBenchmarks from '../data/paperBenchmarks.js';

const { energy } = paperBenchmarks;

const energyMetrics = [
  { label: 'Single-channel energy', value: `${energy.single_channel_energy_mj.toFixed(2)}mJ` },
  { label: 'CRT energy', value: `${energy.crt_energy_mj.toFixed(2)}mJ` },
  { label: 'Energy reduction', value: `${energy.energy_reduction_percent}%` },
  { label: 'Sensor lifetime', value: `${energy.sensor_lifetime_days.toLocaleString()} days / ${energy.sensor_lifetime_years} years` },
];

function EnergyBenchmark() {
  return (
    <section className="rounded-2xl border border-emerald-300/20 bg-emerald-400/10 p-4">
      <div className="mb-4">
        <h3 className="text-lg font-semibold text-white">Energy benchmark</h3>
        <p className="text-xs font-semibold uppercase tracking-wide text-emerald-200">Paper-reported benchmark results</p>
      </div>
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {energyMetrics.map((metric) => (
          <div key={metric.label} className="rounded-xl bg-slate-950/60 p-3">
            <p className="text-xs uppercase tracking-wide text-emerald-100/70">{metric.label}</p>
            <p className="mt-1 text-2xl font-bold text-white">{metric.value}</p>
          </div>
        ))}
      </div>
    </section>
  );
}

export default EnergyBenchmark;
