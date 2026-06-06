import { useEffect, useMemo, useState } from 'react';

function flattenZones(payload) {
  const zones = Array.isArray(payload) ? payload : payload?.zones ?? [];
  return zones.flatMap((zone) => (zone.sensors ?? zone.devices ?? []).map((sensor) => ({ ...sensor, zone: sensor.zone ?? zone.name ?? zone.zone })));
}

function normalizeAudit(payload) {
  return (Array.isArray(payload) ? payload : payload?.events ?? payload?.audit ?? []).map((event) => ({
    ...event,
    decision: event.decision ?? event.result,
    user: event.user ?? event.subject,
    time: event.timestamp ?? event.time ?? event.createdAt,
  }));
}

function buildAlerts(sensors, audit) {
  const now = Date.now();
  const alerts = [];

  sensors.forEach((sensor) => {
    const certExpiry = sensor.certificateExpiresAt ?? sensor.certExpiry ?? sensor.cert_expires_at;
    if (certExpiry) {
      const days = (new Date(certExpiry).getTime() - now) / 86400000;
      if (days >= 0 && days <= 30) alerts.push({ type: 'certificate', text: `${sensor.id ?? sensor.sensorId} certificate expires in ${Math.ceil(days)} day(s).` });
    }

    const lastSeen = sensor.lastSeen ?? sensor.last_seen;
    if (lastSeen && (now - new Date(lastSeen).getTime()) / 60000 > 60) {
      alerts.push({ type: 'offline', text: `${sensor.id ?? sensor.sensorId} is offline in ${sensor.zone}.` });
    }
  });

  audit.filter((event) => event.decision === 'REVOKE').slice(0, 5).forEach((event) => {
    alerts.push({ type: 'revocation', text: `Revocation event for ${event.user ?? 'unknown user'} at ${new Date(event.time ?? now).toLocaleString()}.` });
  });

  const deniesByUser = audit.filter((event) => event.decision === 'DENY' && now - new Date(event.time ?? 0).getTime() <= 3600000)
    .reduce((acc, event) => ({ ...acc, [event.user]: (acc[event.user] ?? 0) + 1 }), {});
  Object.entries(deniesByUser).filter(([, count]) => count >= 3).forEach(([user, count]) => {
    alerts.push({ type: 'deny', text: `${count} DENY decisions for ${user} in the last hour.` });
  });

  return alerts;
}

function AlertPanel({ apiFetch }) {
  const [sensors, setSensors] = useState([]);
  const [audit, setAudit] = useState([]);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;

    async function loadAlerts() {
      try {
        const [zonePayload, auditPayload] = await Promise.all([apiFetch('/api/zones'), apiFetch('/api/audit')]);
        if (!cancelled) {
          setSensors(flattenZones(zonePayload));
          setAudit(normalizeAudit(auditPayload));
          setError('');
        }
      } catch (err) {
        if (!cancelled) setError(err.message);
      }
    }

    loadAlerts();
    const id = window.setInterval(loadAlerts, 60000);
    return () => {
      cancelled = true;
      window.clearInterval(id);
    };
  }, []);

  const alerts = useMemo(() => buildAlerts(sensors, audit), [audit, sensors]);

  return (
    <section className="rounded-3xl border border-slate-700 bg-slate-900/80 p-5 shadow-xl">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-xl font-semibold text-white">Alerts</h2>
          <p className="text-sm text-slate-400">Polls /api/zones and /api/audit every 60 seconds.</p>
        </div>
        <span className="rounded-full bg-slate-800 px-3 py-1 text-sm">{alerts.length} active</span>
      </div>
      {error && <p className="mt-3 rounded-xl bg-amber-400/10 px-3 py-2 text-sm text-amber-100">Alert polling unavailable: {error}</p>}
      <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        {alerts.length === 0 ? <p className="rounded-2xl bg-slate-800/70 p-4 text-sm text-slate-300 md:col-span-2 xl:col-span-4">No generated alerts.</p> : alerts.map((alert, index) => (
          <article key={`${alert.type}-${index}`} className="rounded-2xl border border-amber-300/20 bg-amber-400/10 p-4 text-sm text-amber-50">
            <div className="mb-1 font-semibold uppercase tracking-wide text-amber-200">{alert.type}</div>
            {alert.text}
          </article>
        ))}
      </div>
    </section>
  );
}

export default AlertPanel;
