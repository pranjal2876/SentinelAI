import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  Video,
  ShieldAlert,
  Cctv,
  BarChart3,
  ShieldCheck,
} from 'lucide-react';
import clsx from 'clsx';

const nav = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard, end: true },
  { to: '/live', label: 'Live View', icon: Video },
  { to: '/threats', label: 'Threats', icon: ShieldAlert },
  { to: '/cameras', label: 'Cameras', icon: Cctv },
  { to: '/analytics', label: 'Analytics', icon: BarChart3 },
];

export default function Sidebar() {
  return (
    <aside className="w-60 shrink-0 bg-base-800/60 border-r border-base-600/50 flex flex-col">
      <div className="h-16 flex items-center gap-2 px-5 border-b border-base-600/50">
        <ShieldCheck className="text-accent" size={26} />
        <span className="font-bold text-lg tracking-tight">
          Sentinel<span className="text-accent">AI</span>
        </span>
      </div>
      <nav className="flex-1 p-3 space-y-1">
        {nav.map(({ to, label, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) =>
              clsx(
                'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors',
                isActive
                  ? 'bg-accent/15 text-accent shadow-glow'
                  : 'text-slate-400 hover:bg-base-700 hover:text-slate-200',
              )
            }
          >
            <Icon size={18} />
            {label}
          </NavLink>
        ))}
      </nav>
      <div className="p-4 text-xs text-slate-600 border-t border-base-600/50">
        v1.0.0 · DRDO Edition
      </div>
    </aside>
  );
}
