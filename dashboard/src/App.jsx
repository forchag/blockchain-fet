import AlertPanel from './components/AlertPanel.jsx';
import BenchmarkSummary from './components/BenchmarkSummary.jsx';
import CryptoTimingTable from './components/CryptoTimingTable.jsx';
import EnergyBenchmark from './components/EnergyBenchmark.jsx';
import FormalVerificationBenchmark from './components/FormalVerificationBenchmark.jsx';
import PerformanceCards from './components/PerformanceCards.jsx';
import RevocationBenchmark from './components/RevocationBenchmark.jsx';
import SecurityBenchmark from './components/SecurityBenchmark.jsx';
import AuditLog from './components/AuditLog.jsx';
import RoleManager from './components/RoleManager.jsx';
import SensorFeed from './components/SensorFeed.jsx';
import ZoneMap from './components/ZoneMap.jsx';
import RawDataOverview from './components/RawDataOverview.jsx';
import RawThroughputChart from './components/RawThroughputChart.jsx';
import RawLatencyChart from './components/RawLatencyChart.jsx';
import RawEnergyChart from './components/RawEnergyChart.jsx';
import RawSecurityTable from './components/RawSecurityTable.jsx';

export const API_BASE = 'http://localhost:8080';

export async function apiFetch(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...(options.headers ?? {}) },
    ...options,
  });
  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}`);
  }
  return response.json();
}

function App() {
  return (
    <main className="min-h-screen bg-slate-950 px-4 py-6 text-slate-100 sm:px-6 lg:px-8">
      <div className="mx-auto flex max-w-7xl flex-col gap-6">
        <header className="rounded-3xl border border-cyan-400/20 bg-slate-900/80 p-6 shadow-2xl shadow-cyan-950/30">
          <p className="text-sm uppercase tracking-[0.4em] text-cyan-300">FET Access Control</p>
          <div className="mt-3 flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <h1 className="text-3xl font-bold text-white sm:text-4xl">Farm zone security dashboard</h1>
              <p className="mt-2 max-w-3xl text-slate-300">
                Live sensor health, role delegation, cross-zone activity, and immutable authorization audit events from the local Flask gateway.
              </p>
            </div>
            <div className="rounded-2xl bg-cyan-400/10 px-4 py-3 text-sm text-cyan-100 ring-1 ring-cyan-300/20">
              API endpoint: <span className="font-mono">http://localhost:8080</span>
            </div>
          </div>
        </header>

        <BenchmarkSummary>
          <PerformanceCards />
          <section className="grid gap-6 xl:grid-cols-2">
            <SecurityBenchmark />
            <EnergyBenchmark />
          </section>
          <CryptoTimingTable />
          <section className="grid gap-6 xl:grid-cols-[1.15fr_0.85fr]">
            <RevocationBenchmark />
            <FormalVerificationBenchmark />
          </section>
        </BenchmarkSummary>

        <AlertPanel apiFetch={apiFetch} />

        <section className="grid gap-6 xl:grid-cols-[1.35fr_0.65fr]">
          <ZoneMap apiFetch={apiFetch} />
          <SensorFeed />
        </section>

        <section className="grid gap-6 xl:grid-cols-[0.95fr_1.05fr]">
          <RoleManager apiFetch={apiFetch} />
          <AuditLog apiFetch={apiFetch} />
        </section>

        <section className="rounded-3xl border border-cyan-400/20 bg-slate-900/80 p-6 shadow-2xl shadow-cyan-950/20">
          <div className="mb-5 flex flex-col gap-2 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <p className="text-sm font-semibold uppercase tracking-[0.28em] text-cyan-300">Benchmark data</p>
              <h2 className="mt-2 text-2xl font-bold text-white">Benchmark Data</h2>
            </div>
          </div>
          <div className="flex flex-col gap-6">
            <RawDataOverview apiFetch={apiFetch} />
            <section className="grid gap-6 xl:grid-cols-[1.4fr_0.6fr]">
              <RawThroughputChart apiFetch={apiFetch} />
              <RawEnergyChart apiFetch={apiFetch} />
            </section>
            <RawLatencyChart apiFetch={apiFetch} />
            <RawSecurityTable apiFetch={apiFetch} />
          </div>
        </section>
      </div>
    </main>
  );
}

export default App;
