import { useEffect, useState } from 'react';
import { Plus, Trash2, Play, Square } from 'lucide-react';
import { cameraApi } from '@/services/api';
import type { Camera } from '@/types';

const EMPTY = { camera_id: '', name: '', source: '0', location: '' };

export default function Cameras() {
  const [cameras, setCameras] = useState<Camera[]>([]);
  const [form, setForm] = useState(EMPTY);
  const [showForm, setShowForm] = useState(false);
  const [error, setError] = useState('');

  // Wrap in a block body so the effect returns undefined (not the fetch
  // Promise). Passing `load` directly makes React treat the returned Promise
  // as a cleanup function and crash when it tries to call it.
  const load = () => {
    cameraApi.list().then(setCameras).catch(() => {});
  };
  useEffect(() => {
    load();
  }, []);

  const create = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    try {
      await cameraApi.create(form);
      setForm(EMPTY);
      setShowForm(false);
      load();
    } catch {
      setError('Could not create camera. camera_id must be unique.');
    }
  };

  const remove = async (id: string) => {
    if (!confirm(`Delete camera ${id}?`)) return;
    await cameraApi.remove(id);
    load();
  };

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Camera Management</h2>
        <button className="btn-primary" onClick={() => setShowForm((s) => !s)}>
          <Plus size={16} /> Add Camera
        </button>
      </div>

      {showForm && (
        <form onSubmit={create} className="card p-5 grid grid-cols-1 md:grid-cols-4 gap-3">
          <input className="input" placeholder="camera_id (e.g. gate-01)"
            value={form.camera_id} onChange={(e) => setForm({ ...form, camera_id: e.target.value })} required />
          <input className="input" placeholder="Name"
            value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
          <input className="input" placeholder="Source (0 / rtsp:// / file.mp4)"
            value={form.source} onChange={(e) => setForm({ ...form, source: e.target.value })} required />
          <input className="input" placeholder="Location"
            value={form.location} onChange={(e) => setForm({ ...form, location: e.target.value })} />
          {error && <p className="text-xs text-threat-critical md:col-span-4">{error}</p>}
          <div className="md:col-span-4">
            <button className="btn-primary" type="submit">Save Camera</button>
          </div>
        </form>
      )}

      <div className="card overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-base-900/60 text-slate-400 text-xs uppercase">
            <tr>
              <th className="text-left p-3">ID</th>
              <th className="text-left p-3">Name</th>
              <th className="text-left p-3">Source</th>
              <th className="text-left p-3">Location</th>
              <th className="text-left p-3">Status</th>
              <th className="text-right p-3">Actions</th>
            </tr>
          </thead>
          <tbody>
            {cameras.map((c) => (
              <tr key={c.camera_id} className="border-t border-base-600/40 hover:bg-base-700/30">
                <td className="p-3 font-mono text-xs">{c.camera_id}</td>
                <td className="p-3">{c.name}</td>
                <td className="p-3 text-slate-400 max-w-[200px] truncate">{c.source}</td>
                <td className="p-3 text-slate-400">{c.location}</td>
                <td className="p-3 capitalize">{c.status}</td>
                <td className="p-3">
                  <div className="flex items-center justify-end gap-2">
                    {c.status === 'online' ? (
                      <button className="btn-ghost !p-1.5" onClick={() => cameraApi.stop(c.camera_id).then(load)}>
                        <Square size={15} />
                      </button>
                    ) : (
                      <button className="btn-ghost !p-1.5" onClick={() => cameraApi.start(c.camera_id).then(load)}>
                        <Play size={15} />
                      </button>
                    )}
                    <button className="btn-ghost !p-1.5 text-threat-critical" onClick={() => remove(c.camera_id)}>
                      <Trash2 size={15} />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
            {cameras.length === 0 && (
              <tr><td colSpan={6} className="p-8 text-center text-slate-500">No cameras yet.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
