import { useEffect, useState } from 'react';
import { FileDown, FileSpreadsheet } from 'lucide-react';
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Cell,
} from 'recharts';
import { analyticsApi } from '@/services/api';
import { titleCase } from '@/utils/format';
import type { DashboardStats } from '@/types';

export default function Analytics() {
  const [stats, setStats] = useState<DashboardStats | null>(null);

  useEffect(() => {
    analyticsApi.dashboard().then(setStats).catch(() => {});
  }, []);

  const end = Math.floor(Date.now() / 1000);
  const start = end - 7 * 24 * 3600;

  const byCamera = stats
    ? Object.entries(stats.by_camera).map(([camera, count]) => ({ camera, count }))
    : [];

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Analytics &amp; Reports</h2>
        <div className="flex gap-2">
          <a className="btn-ghost" href={analyticsApi.reportUrl(start, end, 'pdf')} target="_blank" rel="noreferrer">
            <FileDown size={16} /> Export PDF
          </a>
          <a className="btn-ghost" href={analyticsApi.reportUrl(start, end, 'xlsx')} target="_blank" rel="noreferrer">
            <FileSpreadsheet size={16} /> Export Excel
          </a>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="card p-5">
          <h3 className="font-semibold mb-4">Threats per Camera</h3>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={byCamera} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" stroke="#1f2940" />
              <XAxis type="number" tick={{ fill: '#64748b', fontSize: 11 }} allowDecimals={false} />
              <YAxis type="category" dataKey="camera" tick={{ fill: '#64748b', fontSize: 11 }} width={90} />
              <Tooltip contentStyle={{ background: '#0f1524', border: '1px solid #1f2940' }} />
              <Bar dataKey="count" radius={[0, 4, 4, 0]} fill="#00e5ff" />
            </BarChart>
          </ResponsiveContainer>
        </div>
        <div className="card p-5">
          <h3 className="font-semibold mb-4">Category Frequency</h3>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={stats?.by_category ?? []}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1f2940" />
              <XAxis dataKey="category" tick={{ fill: '#64748b', fontSize: 10 }} tickFormatter={titleCase} />
              <YAxis tick={{ fill: '#64748b', fontSize: 11 }} allowDecimals={false} />
              <Tooltip contentStyle={{ background: '#0f1524', border: '1px solid #1f2940' }} />
              <Bar dataKey="count" radius={[4, 4, 0, 0]} fill="#8b5cf6">
                {(stats?.by_category ?? []).map((_, i) => <Cell key={i} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
