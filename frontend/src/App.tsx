import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Sidebar from './components/Sidebar';
import Dashboard from './pages/Dashboard';
import LiveAnalysis from './pages/LiveAnalysis';
import History from './pages/History';
import { VoiceCommandProvider } from './context/VoiceCommandContext';

function App() {
  return (
    <Router>
      <VoiceCommandProvider>
        <div className="flex h-screen w-full overflow-hidden bg-background">
          <Sidebar />
          <main className="flex-1 h-full overflow-y-auto overflow-x-hidden p-6">
            <Routes>
              <Route path="/" element={<Navigate to="/dashboard" replace />} />
              <Route path="/dashboard" element={<Dashboard />} />
              <Route path="/live" element={<LiveAnalysis />} />
              <Route path="/history" element={<History />} />
            </Routes>
          </main>
        </div>
      </VoiceCommandProvider>
    </Router>
  );
}

export default App;
