import { LogOut, Wifi, WifiOff } from 'lucide-react';
import { useAuth } from '@/store/useAuth';

export default function TopBar({ connected }: { connected: boolean }) {
  const { user, logout } = useAuth();
  return (
    <header className="h-16 shrink-0 flex items-center justify-between px-6 border-b border-base-600/50 bg-base-800/40 backdrop-blur">
      <div>
        <h1 className="text-sm text-slate-400">Surveillance Command Center</h1>
        <p className="text-xs text-slate-600">
          {new Date().toLocaleDateString(undefined, {
            weekday: 'long',
            year: 'numeric',
            month: 'long',
            day: 'numeric',
          })}
        </p>
      </div>
      <div className="flex items-center gap-4">
        <span
          className={`flex items-center gap-1.5 text-xs font-medium ${
            connected ? 'text-threat-low' : 'text-threat-critical'
          }`}
        >
          {connected ? <Wifi size={15} /> : <WifiOff size={15} />}
          {connected ? 'Live' : 'Disconnected'}
        </span>
        <div className="text-right">
          <p className="text-sm font-medium text-slate-200">{user?.full_name || user?.username}</p>
          <p className="text-xs text-slate-500 capitalize">{user?.role}</p>
        </div>
        <button onClick={logout} className="btn-ghost !p-2" title="Log out">
          <LogOut size={18} />
        </button>
      </div>
    </header>
  );
}
