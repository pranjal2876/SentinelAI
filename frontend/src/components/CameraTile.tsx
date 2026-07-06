import { useEffect, useRef, useState } from 'react';
import { Play, Square, Loader2, VideoOff } from 'lucide-react';
import clsx from 'clsx';
import type { Camera } from '@/types';

const WS_BASE = import.meta.env.VITE_WS_BASE_URL || `ws://${window.location.host}`;

interface Props {
  camera: Camera;
  onStart: (id: string) => void;
  onStop: (id: string) => void;
}

/** Renders a single live camera tile, streaming annotated JPEG frames over WS. */
export default function CameraTile({ camera, onStart, onStop }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [streaming, setStreaming] = useState(false);

  useEffect(() => {
    if (camera.status !== 'online') {
      setStreaming(false);
      return;
    }
    const ws = new WebSocket(`${WS_BASE}/ws/stream/${camera.camera_id}`);
    ws.binaryType = 'blob';
    ws.onmessage = async (evt) => {
      if (!(evt.data instanceof Blob)) return;
      setStreaming(true);
      const bitmap = await createImageBitmap(evt.data);
      const canvas = canvasRef.current;
      if (!canvas) return;
      canvas.width = bitmap.width;
      canvas.height = bitmap.height;
      canvas.getContext('2d')?.drawImage(bitmap, 0, 0);
      bitmap.close();
    };
    ws.onclose = () => setStreaming(false);
    return () => ws.close();
  }, [camera.status, camera.camera_id]);

  const online = camera.status === 'online';

  return (
    <div className="card overflow-hidden group">
      <div className="relative aspect-video bg-black flex items-center justify-center">
        {streaming ? (
          <canvas ref={canvasRef} className="w-full h-full object-contain" />
        ) : (
          <div className="flex flex-col items-center gap-2 text-slate-600">
            {camera.status === 'connecting' ? (
              <Loader2 className="animate-spin" />
            ) : (
              <VideoOff />
            )}
            <span className="text-xs">{online ? 'Waiting for frames…' : 'Offline'}</span>
          </div>
        )}
        <div className="absolute top-2 left-2 flex items-center gap-1.5">
          <span
            className={clsx(
              'w-2 h-2 rounded-full',
              online ? 'bg-threat-low animate-pulseGlow' : 'bg-slate-600',
            )}
          />
          <span className="text-xs font-medium bg-black/50 px-1.5 py-0.5 rounded">
            {camera.name}
          </span>
        </div>
        {online && (
          <span className="absolute top-2 right-2 text-[11px] bg-black/50 px-1.5 py-0.5 rounded font-mono">
            {camera.fps.toFixed(1)} FPS
          </span>
        )}
      </div>
      <div className="flex items-center justify-between p-3">
        <div>
          <p className="text-sm font-medium">{camera.location || camera.camera_id}</p>
          <p className="text-xs text-slate-500 capitalize">{camera.status}</p>
        </div>
        {online ? (
          <button className="btn-ghost !py-1.5 !px-3" onClick={() => onStop(camera.camera_id)}>
            <Square size={14} /> Stop
          </button>
        ) : (
          <button className="btn-primary !py-1.5 !px-3" onClick={() => onStart(camera.camera_id)}>
            <Play size={14} /> Start
          </button>
        )}
      </div>
    </div>
  );
}
