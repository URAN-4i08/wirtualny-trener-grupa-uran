import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Sidebar from './components/Sidebar';
import Dashboard from './pages/Dashboard';
import LiveAnalysis from './pages/LiveAnalysis';
import History from './pages/History';
import Warmup from './pages/Warmup';
import Login from './pages/Login';
import Register from './pages/Register';
import { VoiceCommandProvider } from './context/VoiceCommandContext';
import { AuthProvider, useAuth } from './context/AuthContext';

const ProtectedRoute = ({ children }: { children: React.ReactNode }) => {
  const { user } = useAuth();
  if (!user) return <Navigate to="/login" replace />;
  return <>{children}</>;
};

const StartRoute = () => {
  const { user } = useAuth();
  return <Navigate to={user ? '/dashboard' : '/login'} replace />;
};

const Layout = ({ children }: { children: React.ReactNode }) => {
  return (
    <div className="flex h-screen w-full overflow-hidden bg-background">
      <Sidebar />
      <main className="flex-1 h-full overflow-y-auto overflow-x-hidden p-6">
        {children}
      </main>
    </div>
  );
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
            <Route path="/dashboard" element={<ProtectedRoute><Layout><Dashboard /></Layout></ProtectedRoute>} />
            <Route path="/warmup" element={<ProtectedRoute><Layout><Warmup /></Layout></ProtectedRoute>} />
            <Route path="/live" element={<ProtectedRoute><Layout><LiveAnalysis /></Layout></ProtectedRoute>} />
            <Route path="/history" element={<ProtectedRoute><Layout><History /></Layout></ProtectedRoute>} />
          </Routes>
        </VoiceCommandProvider>
      </Router>
    </AuthProvider>
  );
}

export default App;
