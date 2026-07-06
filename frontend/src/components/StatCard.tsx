import { motion } from 'framer-motion';
import type { LucideIcon } from 'lucide-react';

interface Props {
  label: string;
  value: string | number;
  icon: LucideIcon;
  accent?: string;
  sub?: string;
}

export default function StatCard({ label, value, icon: Icon, accent = '#00e5ff', sub }: Props) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className="card card-hover p-5 flex items-center justify-between"
    >
      <div>
        <p className="text-slate-400 text-sm">{label}</p>
        <p className="text-3xl font-bold text-slate-100 mt-1">{value}</p>
        {sub && <p className="text-xs text-slate-500 mt-1">{sub}</p>}
      </div>
      <div
        className="p-3 rounded-xl"
        style={{ background: `${accent}22`, color: accent }}
      >
        <Icon size={26} />
      </div>
    </motion.div>
  );
}
