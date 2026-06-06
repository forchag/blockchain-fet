import { useEffect, useState } from 'react';

const LIVE_URL = 'http://localhost:8080/api/sensors/live';

function parseEvent(event) {
  try {
    return JSON.parse(event.data);
  } catch {
    return { sensorId: 'unknown', value: event.data, timestamp: new Date().toISOString() };
  }
}

function SensorFeed() {
  const [readings, setReadings] = useState([]);
  const [status, setStatus] = useState('connecting');

  useEffect(() => {
    const source = new EventSource(LIVE_URL);
    source.onopen = () => setStatus('connected');
    source.onerror = () => setStatus('reconnecting');
    source.onmessage = (event) => {
      const reading = parseEvent(event);
      setReadings((current) => [reading, ...current].slice(0, 50));
    };
    return () => source.close();
  }, []);

  return (
    <section className="rounded-3xl border border-slate-700 bg-slate-900/80 p-5 shadow-xl">
      <div className="mb-4 flex items-center justify-between gap-3">
        <div>
          <h2 className="text-xl font-semibold text-white">Live sensor feed</h2>
          <p className="text-sm text-slate-400">Server-sent events from /api/sensors/live, capped at the latest 50 readings.</p>
        </div>
        <span className={`rounded-full px-3 py-1 text-xs font-semibold ${status === 'connected' ? 'bg-emerald-400/10 text-emerald-200' : 'bg-yellow-400/10 text-yellow-200'}`}>{status}</span>
      </div>
      <div className="max-h-[520px] space-y-3 overflow-auto pr-1">
        {readings.length === 0 ? (
          <p className="rounded-2xl bg-slate-800/70 p-4 text-sm text-slate-300">Waiting for live readings…</p>
        ) : readings.map((reading, index) => (
          <article key={`${reading.id ?? reading.sensorId ?? index}-${reading.timestamp ?? index}`} className="rounded-2xl bg-slate-800/70 p-3">
            <div className="flex items-center justify-between gap-3">
              <span className="font-mono text-sm text-cyan-200">{reading.sensorId ?? reading.sensor_id ?? reading.id ?? 'sensor'}</span>
              <time className="text-xs text-slate-400">{new Date(reading.timestamp ?? reading.time ?? Date.now()).toLocaleString()}</time>
            </div>
            <div className="mt-2 grid grid-cols-2 gap-2 text-sm text-slate-300">
              <span>Zone: <strong className="text-white">{reading.zone ?? 'unknown'}</strong></span>
              <span>Value: <strong className="text-white">{reading.value ?? reading.moisture ?? reading.temperature ?? 'n/a'}</strong></span>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

export default SensorFeed;
