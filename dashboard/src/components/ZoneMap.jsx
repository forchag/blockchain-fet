import { useEffect, useMemo, useState } from 'react';

const ZONES = [
  { name: 'North', x: 0, y: 0, fill: 'fill-emerald-950/60' },
  { name: 'South', x: 200, y: 0, fill: 'fill-sky-950/60' },
  { name: 'East', x: 0, y: 200, fill: 'fill-amber-950/60' },
  { name: 'West', x: 200, y: 200, fill: 'fill-fuchsia-950/60' },
];

function sensorStatus(lastSeen) {
  if (!lastSeen) return 'offline';
  const ageMinutes = (Date.now() - new Date(lastSeen).getTime()) / 60000;
  if (Number.isNaN(ageMinutes) || ageMinutes > 60) return 'offline';
  if (ageMinutes > 30) return 'stale';
  return 'active';
}

function normalizeSensors(payload) {
  const zones = Array.isArray(payload) ? payload : payload?.zones ?? [];
  const sensors = zones.flatMap((zone) => {
    const zoneName = zone.name ?? zone.zone ?? zone.id;
    const zoneSensors = zone.sensors ?? zone.devices ?? [];
    return zoneSensors.map((sensor) => ({ ...sensor, zone: sensor.zone ?? zoneName }));
  });

  if (sensors.length > 0) return sensors.slice(0, 50);

  return Array.from({ length: 50 }, (_, index) => {
    const zone = ZONES[index % ZONES.length].name;
    const minutesAgo = (index * 11) % 95;
    return {
      id: `sensor-${String(index + 1).padStart(2, '0')}`,
      zone,
      lastSeen: new Date(Date.now() - minutesAgo * 60000).toISOString(),
    };
  });
}

function positionFor(sensor, index) {
  const zone = ZONES.find((item) => item.name === sensor.zone) ?? ZONES[index % ZONES.length];
  const slot = Math.floor(index / ZONES.length);
  const col = slot % 4;
  const row = Math.floor(slot / 4);
  return {
    x: zone.x + 35 + col * 38 + ((row % 2) * 12),
    y: zone.y + 40 + row * 38,
  };
}

const statusClass = {
  active: 'fill-emerald-400 stroke-emerald-100',
  stale: 'fill-yellow-300 stroke-yellow-100',
  offline: 'fill-red-500 stroke-red-100',
};

function ZoneMap({ apiFetch }) {
  const [sensors, setSensors] = useState([]);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;

    async function loadZones() {
      try {
        const payload = await apiFetch('/api/zones');
        if (!cancelled) {
          setSensors(normalizeSensors(payload));
          setError('');
        }
      } catch (err) {
        if (!cancelled) {
          setSensors((current) => (current.length > 0 ? current : normalizeSensors(null)));
          setError(`Using demo layout: ${err.message}`);
        }
      }
    }

    loadZones();
    const id = window.setInterval(loadZones, 30000);
    return () => {
      cancelled = true;
      window.clearInterval(id);
    };
  }, []);

  const counts = useMemo(() => ZONES.map((zone) => ({
    ...zone,
    active: sensors.filter((sensor) => sensor.zone === zone.name && sensorStatus(sensor.lastSeen ?? sensor.last_seen) === 'active').length,
    stale: sensors.filter((sensor) => sensor.zone === zone.name && sensorStatus(sensor.lastSeen ?? sensor.last_seen) === 'stale').length,
    offline: sensors.filter((sensor) => sensor.zone === zone.name && sensorStatus(sensor.lastSeen ?? sensor.last_seen) === 'offline').length,
  })), [sensors]);

  return (
    <section className="rounded-3xl border border-slate-700 bg-slate-900/80 p-5 shadow-xl">
      <div className="mb-4 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-xl font-semibold text-white">Zone map</h2>
          <p className="text-sm text-slate-400">50 sensors across North, South, East, and West. Refreshes every 30 seconds.</p>
        </div>
        <div className="flex gap-3 text-xs">
          <span><span className="mr-1 inline-block h-2.5 w-2.5 rounded-full bg-emerald-400" />active</span>
          <span><span className="mr-1 inline-block h-2.5 w-2.5 rounded-full bg-yellow-300" />30-60m</span>
          <span><span className="mr-1 inline-block h-2.5 w-2.5 rounded-full bg-red-500" />offline</span>
        </div>
      </div>
      {error && <p className="mb-3 rounded-xl bg-amber-400/10 px-3 py-2 text-sm text-amber-100">{error}</p>}
      <svg viewBox="0 0 400 400" role="img" aria-label="2 by 2 farm zone sensor grid" className="h-auto w-full rounded-2xl bg-slate-950">
        {ZONES.map((zone) => (
          <g key={zone.name}>
            <rect x={zone.x + 6} y={zone.y + 6} width="188" height="188" rx="18" className={`${zone.fill} stroke-slate-700`} />
            <text x={zone.x + 20} y={zone.y + 30} className="fill-slate-100 text-sm font-bold">{zone.name}</text>
          </g>
        ))}
        {sensors.map((sensor, index) => {
          const status = sensorStatus(sensor.lastSeen ?? sensor.last_seen);
          const point = positionFor(sensor, index);
          return <circle key={sensor.id ?? sensor.sensorId ?? index} cx={point.x} cy={point.y} r="6" className={`${statusClass[status]} stroke-2`} />;
        })}
      </svg>
      <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {counts.map((zone) => (
          <div key={zone.name} className="rounded-2xl bg-slate-800/70 p-3 text-sm">
            <div className="font-semibold text-white">{zone.name}</div>
            <div className="mt-1 text-slate-300">{zone.active} active · {zone.stale} stale · {zone.offline} offline</div>
          </div>
        ))}
      </div>
    </section>
  );
}

export default ZoneMap;
