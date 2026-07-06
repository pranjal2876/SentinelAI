import { useEffect, useState } from 'react';
import { Check, Info, Search } from 'lucide-react';
import SeverityBadge from '@/components/SeverityBadge';
import { threatApi } from '@/services/api';
import { fmtDateTime, titleCase } from '@/utils/format';
import type { Threat, ThreatExplanation } from '@/types';

const CATEGORIES = [
  '', 'intrusion', 'loitering', 'abandoned_object', 'crowd', 'running',
  'wrong_direction', 'vehicle_in_zone', 'multiple_intruders', 'camera_tampering',
  'anomaly',
];
const SEVERITIES = ['', 'low', 'medium', 'high', 'critical'];

export default function Threats() {
  const [threats, setThreats] = useState<Threat[]>([]);
  const [category, setCategory] = useState('');
  const [severity, setSeverity] = useState('');
  const [explanation, setExplanation] = useState<ThreatExplanation | null>(null);

  const load = () => {
    const params: Record<string, string> = {};
    if (category) params.category = category;
    if (severity) params.severity = severity;
    threatApi.list(params).then(setThreats).catch(() => {});
  };

  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { load(); }, [category, severity]);

  const ack = async (id: number) => {
    await threatApi.acknowledge(id);
    load();
  };
  const explain = async (id: number) => {
    setExplanation(await threatApi.explain(id));
  };

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center gap-3 flex-wrap">
        <h2 className="text-lg font-semibold mr-auto">Threat History</h2>
        <div className="flex items-center gap-1.5 text-slate-500">
          <Search size={16} />
          <span className="text-xs">Filters</span>
        </div>
        <select className="input !w-auto" value={category} onChange={(e) => setCategory(e.target.value)}>
          {CATEGORIES.map((c) => (
            <option key={c} value={c}>{c ? titleCase(c) : 'All categories'}</option>
          ))}
        </select>
        <select className="input !w-auto" value={severity} onChange={(e) => setSeverity(e.target.value)}>
          {SEVERITIES.map((s) => (
            <option key={s} value={s}>{s ? s.toUpperCase() : 'All severities'}</option>
          ))}
        </select>
      </div>

      <div className="card overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-base-900/60 text-slate-400 text-xs uppercase">
            <tr>
              <th className="text-left p-3">Time</th>
              <th className="text-left p-3">Camera</th>
              <th className="text-left p-3">Category</th>
              <th className="text-left p-3">Severity</th>
              <th className="text-left p-3">Score</th>
              <th className="text-left p-3">Message</th>
              <th className="text-right p-3">Actions</th>
            </tr>
          </thead>
          <tbody>
            {threats.map((t) => (
              <tr key={t.id} className="border-t border-base-600/40 hover:bg-base-700/30">
                <td className="p-3 text-slate-400 whitespace-nowrap">{fmtDateTime(t.timestamp)}</td>
                <td className="p-3">{t.camera_id}</td>
                <td className="p-3">{titleCase(t.category)}</td>
                <td className="p-3"><SeverityBadge severity={t.severity} /></td>
                <td className="p-3 font-mono">{t.score.toFixed(2)}</td>
                <td className="p-3 text-slate-400 max-w-xs truncate">{t.message}</td>
                <td className="p-3">
                  <div className="flex items-center justify-end gap-2">
                    <button className="btn-ghost !p-1.5" title="Explain" onClick={() => explain(t.id)}>
                      <Info size={15} />
                    </button>
                    {!t.acknowledged && (
                      <button className="btn-ghost !p-1.5" title="Acknowledge" onClick={() => ack(t.id)}>
                        <Check size={15} />
                      </button>
                    )}
                    {t.acknowledged && <span className="badge bg-threat-low/20 text-threat-low">ACK</span>}
                  </div>
                </td>
              </tr>
            ))}
            {threats.length === 0 && (
              <tr>
                <td colSpan={7} className="p-8 text-center text-slate-500">No threats found.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {explanation && (
        <div className="card p-5 border-accent/30">
          <div className="flex items-center justify-between mb-2">
            <h3 className="font-semibold flex items-center gap-2">
              <Info size={18} className="text-accent" /> Explainable AI — Why did this fire?
            </h3>
            <button className="btn-ghost !py-1 !px-2 text-xs" onClick={() => setExplanation(null)}>Close</button>
          </div>
          <p className="text-sm text-slate-300 mb-2">{explanation.why}</p>
          <p className="text-xs text-slate-500 mb-3">
            Confidence: {(explanation.confidence * 100).toFixed(0)}% · Severity: {explanation.severity}
          </p>
          <div className="flex flex-wrap gap-2">
            {explanation.contributing_factors.map((f, i) => (
              <span key={i} className="badge bg-base-700 text-slate-300">
                {f.factor}: {String(f.value)}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
