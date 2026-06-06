function BenchmarkSummary({ children }) {
  return (
    <section className="rounded-3xl border border-cyan-400/20 bg-slate-900/80 p-6 shadow-2xl shadow-cyan-950/20">
      <div className="mb-5 flex flex-col gap-2 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.28em] text-cyan-300">Paper-reported benchmark results</p>
          <h2 className="mt-2 text-2xl font-bold text-white">Paper-Reported Benchmark Results</h2>
          <p className="mt-2 max-w-4xl text-sm text-slate-300">
            These values reproduce the benchmark results stated in the paper. Live benchmark runs are stored separately under results/.
          </p>
        </div>
        <span className="w-fit rounded-full border border-cyan-300/30 bg-cyan-400/10 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-cyan-100">
          Paper-reported benchmark results
        </span>
      </div>
      <div className="flex flex-col gap-6">{children}</div>
    </section>
  );
}

export default BenchmarkSummary;
