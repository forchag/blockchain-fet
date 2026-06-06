import { useEffect, useMemo, useState } from 'react';

const PAGE_SIZE = 25;

function normalizeAudit(payload) {
  const rows = Array.isArray(payload) ? payload : payload?.events ?? payload?.audit ?? [];
  return rows.map((row, index) => ({
    id: row.id ?? row.txId ?? `${row.user ?? 'user'}-${row.timestamp ?? index}`,
    time: row.timestamp ?? row.time ?? row.createdAt ?? new Date().toISOString(),
    user: row.user ?? row.subject ?? 'unknown',
    zone: row.zone ?? row.resourceZone ?? 'unknown',
    decision: row.decision ?? row.result ?? 'UNKNOWN',
    resource: row.resource ?? row.resourceId ?? 'n/a',
    reason: row.reason ?? row.message ?? '',
  }));
}

function AuditLog({ apiFetch }) {
  const [rows, setRows] = useState([]);
  const [filters, setFilters] = useState({ zone: '', decision: '', start: '', end: '' });
  const [page, setPage] = useState(1);
  const [error, setError] = useState('');

  useEffect(() => {
    async function loadAudit() {
      try {
        const query = new URLSearchParams(Object.entries(filters).filter(([, value]) => value));
        const payload = await apiFetch(`/api/audit${query.toString() ? `?${query}` : ''}`);
        setRows(normalizeAudit(payload));
        setError('');
        setPage(1);
      } catch (err) {
        setRows([]);
        setError(err.message);
      }
    }
    loadAudit();
  }, [filters]);

  const filteredRows = useMemo(() => rows.filter((row) => {
    const rowTime = new Date(row.time).getTime();
    const start = filters.start ? new Date(filters.start).getTime() : null;
    const end = filters.end ? new Date(filters.end).getTime() : null;
    return (!filters.zone || row.zone === filters.zone)
      && (!filters.decision || row.decision === filters.decision)
      && (!start || rowTime >= start)
      && (!end || rowTime <= end);
  }), [filters, rows]);

  const totalPages = Math.max(1, Math.ceil(filteredRows.length / PAGE_SIZE));
  const visibleRows = filteredRows.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  function updateFilter(key, value) {
    setFilters((current) => ({ ...current, [key]: value }));
  }

  return (
    <section className="rounded-3xl border border-slate-700 bg-slate-900/80 p-5 shadow-xl">
      <h2 className="text-xl font-semibold text-white">Audit log</h2>
      <p className="text-sm text-slate-400">Filter authorization records by zone, decision, and time window.</p>
      <div className="mt-4 grid gap-3 md:grid-cols-4">
        <select className="rounded-xl border border-slate-700 bg-slate-950 px-3 py-2" value={filters.zone} onChange={(event) => updateFilter('zone', event.target.value)}>
          <option value="">All zones</option><option>North</option><option>South</option><option>East</option><option>West</option>
        </select>
        <select className="rounded-xl border border-slate-700 bg-slate-950 px-3 py-2" value={filters.decision} onChange={(event) => updateFilter('decision', event.target.value)}>
          <option value="">All decisions</option><option>GRANT</option><option>DENY</option><option>REVOKE</option>
        </select>
        <input className="rounded-xl border border-slate-700 bg-slate-950 px-3 py-2" type="datetime-local" value={filters.start} onChange={(event) => updateFilter('start', event.target.value)} aria-label="Start time" />
        <input className="rounded-xl border border-slate-700 bg-slate-950 px-3 py-2" type="datetime-local" value={filters.end} onChange={(event) => updateFilter('end', event.target.value)} aria-label="End time" />
      </div>
      {error && <p className="mt-3 rounded-xl bg-red-500/10 px-3 py-2 text-sm text-red-100">Audit API unavailable: {error}</p>}
      <div className="mt-4 overflow-x-auto">
        <table className="min-w-full text-left text-sm">
          <thead className="text-slate-400"><tr><th className="p-2">Time</th><th className="p-2">User</th><th className="p-2">Zone</th><th className="p-2">Decision</th><th className="p-2">Resource</th></tr></thead>
          <tbody>
            {visibleRows.map((row) => (
              <tr key={row.id} className="border-t border-slate-800"><td className="p-2">{new Date(row.time).toLocaleString()}</td><td className="p-2">{row.user}</td><td className="p-2">{row.zone}</td><td className="p-2 font-semibold">{row.decision}</td><td className="p-2">{row.resource}</td></tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="mt-4 flex items-center justify-between text-sm">
        <button className="rounded-xl bg-slate-800 px-3 py-2 disabled:opacity-40" disabled={page === 1} onClick={() => setPage((current) => Math.max(1, current - 1))}>Previous</button>
        <span>Page {page} of {totalPages} · {filteredRows.length} rows</span>
        <button className="rounded-xl bg-slate-800 px-3 py-2 disabled:opacity-40" disabled={page === totalPages} onClick={() => setPage((current) => Math.min(totalPages, current + 1))}>Next</button>
      </div>
    </section>
  );
}

export default AuditLog;
