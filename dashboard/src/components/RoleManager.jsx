import { useState } from 'react';

const ROLE_TREE = {
  Admin: ['Gateway', 'Farmer'],
  Gateway: ['Sensor'],
  Farmer: ['Viewer'],
};

const initialForm = { user: '', role: 'Sensor', zone: '', expiry: '' };

function TreeNode({ role, childrenByRole }) {
  const children = childrenByRole[role] ?? [];
  return (
    <li className="ml-4 border-l border-slate-700 pl-4">
      <span className="inline-flex rounded-full bg-cyan-400/10 px-3 py-1 text-sm font-semibold text-cyan-100">{role}</span>
      {children.length > 0 && <ul className="mt-3 space-y-3">{children.map((child) => <TreeNode key={child} role={child} childrenByRole={childrenByRole} />)}</ul>}
    </li>
  );
}

function validate(form) {
  if (!form.user.trim()) return 'User is required.';
  if ((form.role === 'Gateway' || form.role === 'Sensor') && !form.zone) return 'Zone is required for Gateway and Sensor roles.';
  if (!form.expiry) return 'Expiry date is required.';
  if (new Date(form.expiry).getTime() <= Date.now()) return 'Expiry date must be in the future.';
  return '';
}

function RoleManager({ apiFetch }) {
  const [form, setForm] = useState(initialForm);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  function update(key, value) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  async function submit(action) {
    const validation = action === 'revoke' ? (!form.user.trim() ? 'User is required.' : '') : validate(form);
    if (validation) {
      setError(validation);
      setMessage('');
      return;
    }

    try {
      await apiFetch(`/api/roles/${action}`, {
        method: 'POST',
        body: JSON.stringify({ ...form, expiresAt: form.expiry }),
      });
      setMessage(`${action} request submitted for ${form.user}.`);
      setError('');
    } catch (err) {
      setError(`Role API unavailable: ${err.message}`);
      setMessage('');
    }
  }

  return (
    <section className="rounded-3xl border border-slate-700 bg-slate-900/80 p-5 shadow-xl">
      <h2 className="text-xl font-semibold text-white">Role manager</h2>
      <p className="text-sm text-slate-400">Assign, renew, and revoke hierarchy-scoped farm roles.</p>
      <div className="mt-5 grid gap-5 lg:grid-cols-[0.8fr_1.2fr]">
        <div className="rounded-2xl bg-slate-950/80 p-4">
          <h3 className="mb-3 font-semibold text-white">Hierarchy</h3>
          <ul className="space-y-3"><TreeNode role="Admin" childrenByRole={ROLE_TREE} /></ul>
        </div>
        <form className="grid gap-3" onSubmit={(event) => event.preventDefault()}>
          <input className="rounded-xl border border-slate-700 bg-slate-950 px-3 py-2" placeholder="User ID" value={form.user} onChange={(event) => update('user', event.target.value)} />
          <div className="grid gap-3 sm:grid-cols-3">
            <select className="rounded-xl border border-slate-700 bg-slate-950 px-3 py-2" value={form.role} onChange={(event) => update('role', event.target.value)}>
              <option>Admin</option><option>Gateway</option><option>Farmer</option><option>Sensor</option><option>Viewer</option>
            </select>
            <select className="rounded-xl border border-slate-700 bg-slate-950 px-3 py-2" value={form.zone} onChange={(event) => update('zone', event.target.value)}>
              <option value="">Zone</option><option>North</option><option>South</option><option>East</option><option>West</option>
            </select>
            <input className="rounded-xl border border-slate-700 bg-slate-950 px-3 py-2" type="datetime-local" value={form.expiry} onChange={(event) => update('expiry', event.target.value)} aria-label="Role expiry" />
          </div>
          <div className="flex flex-wrap gap-3">
            <button className="rounded-xl bg-emerald-500 px-4 py-2 font-semibold text-emerald-950" type="button" onClick={() => submit('assign')}>Assign</button>
            <button className="rounded-xl bg-cyan-500 px-4 py-2 font-semibold text-cyan-950" type="button" onClick={() => submit('renew')}>Renew</button>
            <button className="rounded-xl bg-red-500 px-4 py-2 font-semibold text-red-950" type="button" onClick={() => submit('revoke')}>Revoke</button>
          </div>
          {error && <p className="rounded-xl bg-red-500/10 px-3 py-2 text-sm text-red-100">{error}</p>}
          {message && <p className="rounded-xl bg-emerald-500/10 px-3 py-2 text-sm text-emerald-100">{message}</p>}
        </form>
      </div>
    </section>
  );
}

export default RoleManager;
