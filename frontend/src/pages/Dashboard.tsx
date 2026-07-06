import { useEffect, useState } from 'react';
import {
  ShieldAlert,
  Cctv,
  Activity,
  CalendarClock,
} from 'lucide-react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  AreaChart,
  Area,
  CartesianGrid,
} from 'recharts';
import StatCard from '@/components/StatCard';
import ThreatFeed from '@/components/ThreatFeed';
import { analyticsApi } from '@/services/api';
import { severityColor, titleCase } from '@/utils/format';
import type { DashboardStats, LiveThreat, Severity } from '@/types';

const CAT_COLORS = ['#00e5ff', '#8b5cf6', '#f97316', '#22c55e', '#eab308', '#ec4899', '#14b8a6'];

export default function Dashboard({ liveThreats }: { liveThreats: LiveThreat[] }) {
  const [stats, setStats] = useState<DashboardStats | null>(null);

  useEffect(() => {
    const load = () => analyticsApi.dashboard().then(setStats).catch(() => {});
    load();
    const id = setInterval(load, 10000);
    return () => clearInterval(id);
  }, [liveThreats.length]);

  return (
    <div className="p-6 space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <StatCard label="Total Threats" value={stats?.total_threats ?? '—'} icon={ShieldAlert} accent="#ef4444" />
        <StatCard label="Threats Today" value={stats?.threats_today ?? '—'} icon={CalendarClock} accent="#f97316" />
        <StatCard
          label="Active Cameras"
          value={stats ? `${stats.active_cameras}/${stats.total_cameras}` : '—'}
          icon={Cctv}
          accent="#00e5ff"
        />
        <StatCard label="Live Events" value={liveThreats.length} icon={Activity} accent="#8b5cf6" sub="this session" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 card p-5">
          <h3 className="font-semibold mb-4">Threat Activity (last 24h)</h3>
          <ResponsiveContainer width="100%" height={240}>
            <AreaChart data={stats?.timeline ?? []}>
              <defs>
                <linearGradient id="g1" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#00e5ff" stopOpacity={0.5} />
                  <stop offset="95%" stopColor="#00e5ff" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#1f2940" />
              <XAxis dataKey="bucket" tick={{ fill: '#64748b', fontSize: 11 }}
                tickFormatter={(v) => String(v).slice(11)} />
              <YAxis tick={{ fill: '#64748b', fontSize: 11 }} allowDecimals={false} />
              <Tooltip contentStyle={{ background: '#0f1524', border: '1px solid #1f2940' }} />
              <Area type="monotone" dataKey="count" stroke="#00e5ff" fill="url(#g1)" />
            </AreaChart>
          </ResponsiveContainer>
        </div>
        <div className="h-[340px]">
          <ThreatFeed threats={liveThreats} />
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="card p-5">
          <h3 className="font-semibold mb-4">Threats by Category</h3>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={stats?.by_category ?? []}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1f2940" />
              <XAxis dataKey="category" tick={{ fill: '#64748b', fontSize: 10 }}
                tickFormatter={titleCase} />
              <YAxis tick={{ fill: '#64748b', fontSize: 11 }} allowDecimals={false} />
              <Tooltip contentStyle={{ background: '#0f1524', border: '1px solid #1f2940' }} />
              <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                {(stats?.by_category ?? []).map((_, i) => (
                  <Cell key={i} fill={CAT_COLORS[i % CAT_COLORS.length]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
        <div className="card p-5">
          <h3 className="font-semibold mb-4">Severity Distribution</h3>
          <ResponsiveContainer width="100%" height={260}>
            <PieChart>
              <Pie
                data={stats?.by_severity ?? []}
                dataKey="count"
                nameKey="severity"
                innerRadius={60}
                outerRadius={95}
                paddingAngle={3}
              >
                {(stats?.by_severity ?? []).map((s, i) => (
                  <Cell key={i} fill={severityColor[s.severity as Severity] ?? '#64748b'} />
                ))}
              </Pie>
              <Tooltip contentStyle={{ background: '#0f1524', border: '1px solid #1f2940' }} />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
