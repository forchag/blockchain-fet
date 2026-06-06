import { useEffect, useState } from 'react';

function formatScenario(s) {
  return s.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

function RawSecurityTable({ apiFetch }) {
  const [scenarios, setScenarios] = useState([]);
  const [total, setTotal] = useState(0);
  const [error, setError] = useState('');

  useEffect(() => {
    apiFetch('/api/raw/security')
      .then((d) => {
        setScenarios(d.scenarios);
        setTotal(d.total_attempts);
        setError('');
      })
      .catch((err) => setError(err.message));
  }, [apiFetch]);

  if (error) {
    return <p className="rounded-xl bg-red-900/40 p-4 text-sm text-red-300">{error}</p>;
  }

  return (
    <div>
      <h3 className="mb-3 text-lg font-semibold text-white">Security scenarios — blocked attempts</h3>
      <div className="overflow-x-auto rounded-xl border border-slate-700">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-700 bg-slate-800/80">
              <th className="px-4 py-2 text-left font-semibold text-slate-300">Scenario</th>
              <th className="px-4 py-2 text-right font-semibold text-slate-300">Blocked</th>
              <th className="px-4 py-2 text-right font-semibold text-slate-300">% of total</th>
              <th className="px-4 py-2 text-right font-semibold text-slate-300">Block rate</th>
            </tr>
          </thead>
          <tbody>
            {scenarios.length === 0 && (
              <tr>
                <td colSpan="4" className="px-4 py-6 text-center text-slate-500">Loading…</td>
              </tr>
            )}
            {scenarios.map(({ scenario, blocked_attempts }) => (
              <tr key={scenario} className="border-b border-slate-800 hover:bg-slate-800/40">
                <td className="px-4 py-2 text-slate-200">{formatScenario(scenario)}</td>
                <td className="px-4 py-2 text-right font-mono text-white">{blocked_attempts.toLocaleString()}</td>
                <td className="px-4 py-2 text-right font-mono text-slate-300">
                  {total ? `${((blocked_attempts / total) * 100).toFixed(1)}%` : '—'}
                </td>
                <td className="px-4 py-2 text-right">
                  <span className="rounded-full bg-green-900/40 px-2 py-0.5 text-xs font-semibold text-green-300">
                    100%
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
          {total > 0 && (
            <tfoot>
              <tr className="bg-slate-800/60">
                <td className="px-4 py-2 font-semibold text-slate-300">Total</td>
                <td className="px-4 py-2 text-right font-mono font-bold text-white">{total.toLocaleString()}</td>
                <td className="px-4 py-2 text-right font-mono text-slate-300">100%</td>
                <td className="px-4 py-2 text-right">
                  <span className="rounded-full bg-green-900/40 px-2 py-0.5 text-xs font-semibold text-green-300">
                    100%
                  </span>
                </td>
              </tr>
            </tfoot>
          )}
        </table>
      </div>
    </div>
  );
}

export default RawSecurityTable;
