import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Dashboard from './pages/Dashboard';
import LiveAnalysis from './pages/LiveAnalysis';
import History from './pages/History';
import Warmup from './pages/Warmup';
import Login from './pages/Login';
import Register from './pages/Register';
import VoiceCommands from './pages/VoiceCommands';
import { VoiceCommandProvider } from './context/VoiceCommandContext';
import { AuthProvider, useAuth } from './context/AuthContext';
import AppShell from './components/layout/AppShell';

const ProtectedRoute = ({ children }: { children: React.ReactNode }) => {
  const { user, loading } = useAuth();
  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-navy text-on-surface-variant">
        Ładowanie...
      </div>
    );
  }
  if (!user) return <Navigate to="/login" replace />;
  return <>{children}</>;
};

const StartRoute = () => {
  const { user, loading } = useAuth();
  if (loading) return null;
  return <Navigate to={user ? '/dashboard' : '/login'} replace />;
};

function App() {
  return (
    <AuthProvider>
      <Router>
        <VoiceCommandProvider>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
            <Route path="/" element={<StartRoute />} />
            <Route
              element={
                <ProtectedRoute>
                  <AppShell />
                </ProtectedRoute>
              }
            >
              <Route path="/dashboard" element={<Dashboard />} />
              <Route path="/warmup" element={<Warmup />} />
              <Route path="/live" element={<LiveAnalysis />} />
              <Route path="/history" element={<History />} />
              <Route path="/voice-commands" element={<VoiceCommands />} />
            </Route>
          </Routes>
        </VoiceCommandProvider>
      </Router>
    </AuthProvider>
  );
}

export default App;
