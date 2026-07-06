import { AnimatePresence, motion } from 'framer-motion';
import { AlertTriangle } from 'lucide-react';
import SeverityBadge from './SeverityBadge';
import { fmtTime, titleCase } from '@/utils/format';
import type { LiveThreat } from '@/types';

export default function ThreatFeed({ threats }: { threats: LiveThreat[] }) {
  return (
    <div className="card p-4 h-full flex flex-col">
      <div className="flex items-center gap-2 mb-3">
        <AlertTriangle size={18} className="text-threat-high" />
        <h3 className="font-semibold">Live Threat Feed</h3>
        <span className="ml-auto text-xs text-slate-500">{threats.length} recent</span>
      </div>
      <div className="flex-1 overflow-y-auto space-y-2 pr-1">
        {threats.length === 0 && (
          <p className="text-sm text-slate-500 text-center py-8">
            No active threats. Monitoring…
          </p>
        )}
        <AnimatePresence initial={false}>
          {threats.map((t, i) => (
            <motion.div
              key={`${t.timestamp}-${i}`}
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0 }}
              className="p-3 rounded-lg bg-base-900/60 border border-base-600/40"
            >
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-slate-200">
                  {titleCase(t.category)}
                </span>
                <SeverityBadge severity={t.severity} />
              </div>
              <p className="text-xs text-slate-400 mt-1">{t.message}</p>
              <div className="flex items-center justify-between mt-1.5 text-[11px] text-slate-600">
                <span>{t.camera_id}</span>
                <span>{fmtTime(t.timestamp)}</span>
              </div>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </div>
  );
}
