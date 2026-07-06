import { useEffect } from 'react';
import { Navigate, Route, Routes, useLocation } from 'react-router-dom';
import { Loader2 } from 'lucide-react';
import Sidebar from '@/components/Sidebar';
import TopBar from '@/components/TopBar';
import Login from '@/pages/Login';
import Dashboard from '@/pages/Dashboard';
import LiveView from '@/pages/LiveView';
import Threats from '@/pages/Threats';
import Cameras from '@/pages/Cameras';
import Analytics from '@/pages/Analytics';
import { useAuth } from '@/store/useAuth';
import { useThreatSocket } from '@/hooks/useThreatSocket';

/** Authenticated application shell with sidebar, topbar and routed pages. */
function Shell() {
  const { threats, connected } = useThreatSocket();
  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0">
        <TopBar connected={connected} />
        <main className="flex-1 overflow-y-auto">
          <Routes>
            <Route path="/" element={<Dashboard liveThreats={threats} />} />
            <Route path="/live" element={<LiveView />} />
            <Route path="/threats" element={<Threats />} />
            <Route path="/cameras" element={<Cameras />} />
            <Route path="/analytics" element={<Analytics />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
      </div>
    </div>
  );
}

export default function App() {
  const { user, loading, fetchMe } = useAuth();
  const location = useLocation();

  useEffect(() => {
    fetchMe();
  }, [fetchMe]);

  if (loading) {
    return (
      <div className="h-screen flex items-center justify-center">
        <Loader2 className="animate-spin text-accent" size={32} />
      </div>
    );
  }

  if (!user) {
    return (
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="*" element={<Navigate to="/login" state={{ from: location }} replace />} />
      </Routes>
    );
  }

  return <Shell />;
}
