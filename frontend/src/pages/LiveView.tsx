import { useCallback, useEffect, useState } from 'react';
import { cameraApi } from '@/services/api';
import CameraTile from '@/components/CameraTile';
import type { Camera } from '@/types';

export default function LiveView() {
  const [cameras, setCameras] = useState<Camera[]>([]);

  const load = useCallback(() => {
    cameraApi.list().then(setCameras).catch(() => {});
  }, []);

  useEffect(() => {
    load();
    const id = setInterval(load, 5000);
    return () => clearInterval(id);
  }, [load]);

  const onStart = async (id: string) => {
    await cameraApi.start(id);
    setTimeout(load, 800);
  };
  const onStop = async (id: string) => {
    await cameraApi.stop(id);
    setTimeout(load, 800);
  };

  return (
    <div className="p-6">
      <h2 className="text-lg font-semibold mb-4">Live Camera Feeds</h2>
      {cameras.length === 0 ? (
        <div className="card p-10 text-center text-slate-500">
          No cameras configured. Add one from the <b>Cameras</b> page.
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5">
          {cameras.map((c) => (
            <CameraTile key={c.camera_id} camera={c} onStart={onStart} onStop={onStop} />
          ))}
        </div>
      )}
    </div>
  );
}
