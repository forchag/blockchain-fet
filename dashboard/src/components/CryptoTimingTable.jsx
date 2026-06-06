import paperBenchmarks from '../data/paperBenchmarks.js';

const { crypto_timing: cryptoTiming } = paperBenchmarks;

const timingRows = [
  {
    operation: 'SHA-256 hardware',
    mean: cryptoTiming.sha256_hardware_time_us,
    standardDeviation: cryptoTiming.sha256_hardware_sd_us,
    unit: 'µs',
  },
  {
    operation: 'eFuse key read',
    mean: cryptoTiming.efuse_key_read_time_us,
    standardDeviation: cryptoTiming.efuse_key_read_sd_us,
    unit: 'µs',
  },
  {
    operation: 'Ed25519 sign',
    mean: cryptoTiming.ed25519_sign_time_us,
    standardDeviation: cryptoTiming.ed25519_sign_sd_us,
    unit: 'µs',
  },
  {
    operation: 'Key context',
    mean: cryptoTiming.key_context_time_us,
    standardDeviation: cryptoTiming.key_context_sd_us,
    unit: 'µs',
  },
  {
    operation: 'Total signing',
    mean: cryptoTiming.total_signing_time_us,
    standardDeviation: cryptoTiming.total_signing_sd_us,
    unit: 'µs',
  },
];

function CryptoTimingTable() {
  return (
    <section className="rounded-2xl border border-slate-700 bg-slate-800/60 p-4">
      <div className="mb-4">
        <h3 className="text-lg font-semibold text-white">Cryptographic timing</h3>
        <p className="text-xs font-semibold uppercase tracking-wide text-cyan-300">Paper-reported benchmark results</p>
      </div>
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-slate-700 text-left text-sm">
          <thead className="text-xs uppercase tracking-wide text-slate-400">
            <tr>
              <th scope="col" className="py-2 pr-4 font-semibold">Operation</th>
              <th scope="col" className="px-4 py-2 font-semibold">Mean</th>
              <th scope="col" className="px-4 py-2 font-semibold">Standard deviation</th>
              <th scope="col" className="py-2 pl-4 font-semibold">Unit</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-700 text-slate-200">
            {timingRows.map((row) => (
              <tr key={row.operation}>
                <th scope="row" className="py-3 pr-4 font-medium text-white">{row.operation}</th>
                <td className="px-4 py-3">{row.mean.toLocaleString()}</td>
                <td className="px-4 py-3">{row.standardDeviation.toLocaleString()}</td>
                <td className="py-3 pl-4">{row.unit}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

export default CryptoTimingTable;
