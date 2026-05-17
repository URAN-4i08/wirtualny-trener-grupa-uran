import { useState, useEffect } from 'react';
import { Camera, StopCircle, PlayCircle, AlertTriangle, MonitorPlay, FlaskConical } from 'lucide-react';
import { clsx } from 'clsx';
import { PieChart, Pie, Cell, ResponsiveContainer } from 'recharts';

export default function LiveAnalysis() {
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isTestMode, setIsTestMode] = useState(true); // Włączone domyślnie dla testów lokalnych
  const [currentAngle, setCurrentAngle] = useState(120);
  const [score, setScore] = useState(0);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    if (!isAnalyzing) return;

    if (isTestMode) {
      // Zastępcze dane (Mock) dla testów lokalnych bez backendu
      const interval = setInterval(() => {
        const newAngle = 100 + Math.floor(Math.random() * 60);
        setCurrentAngle(newAngle);
        
        const newScore = Math.floor(Math.random() * 100);
        setScore(newScore);

        if (newAngle > 150) {
          setErrorMsg("Zbyt małe ugięcie kolan!");
        } else if (newScore < 40) {
          setErrorMsg("Wyprostuj łokcie!");
        } else {
          setErrorMsg(null);
        }
      }, 1000);
      return () => clearInterval(interval);
    } else {
      // Połączenie z rzeczywistym backendem FastAPI
      const ws = new WebSocket('ws://localhost:8000/ws/metrics');
      
      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.kneeAngle !== undefined) setCurrentAngle(data.kneeAngle);
          if (data.score !== undefined) setScore(data.score);
          setErrorMsg(data.warnings || null);
        } catch (err) {
          console.error("Error parsing WebSocket data:", err);
        }
      };

      return () => ws.close();
    }
  }, [isAnalyzing, isTestMode]);

  // Data for the score pie chart
  const pieData = [
    { name: 'Punkty', value: score, color: '#4ade80' },
    { name: 'Brakujące', value: 100 - score, color: '#32353c' }
  ];

  return (
    <div className="max-w-6xl mx-auto flex flex-col h-[calc(100vh-3rem)]">
      <header className="flex items-center justify-between mb-6 shrink-0">
        <div>
          <h2 className="text-3xl font-bold text-white mb-2">Analiza Live</h2>
          <p className="text-on-surface-variant">Strumieniowanie z głównej kamery i analiza w czasie rzeczywistym.</p>
        </div>
        <div className="flex gap-4">
          <button 
            onClick={() => setIsTestMode(!isTestMode)}
            className={clsx(
              "flex items-center gap-2 px-4 py-2 rounded-lg border transition",
              isTestMode 
                ? "bg-purple-500/20 text-purple-400 border-purple-500/30" 
                : "bg-surface-variant/50 text-on-surface-variant border-white/10 hover:bg-surface-variant"
            )}
            title="Włącz tryb testowy (bez backendu)"
          >
            <FlaskConical className="w-4 h-4" />
            Tryb Testowy (Mock)
          </button>
          <button className="flex items-center gap-2 bg-surface-variant/50 text-white px-4 py-2 rounded-lg border border-white/10 hover:bg-surface-variant transition">
            <Camera className="w-4 h-4" />
            Dodaj kamerę 2
          </button>
          <button
            onClick={() => setIsAnalyzing(!isAnalyzing)}
            className={clsx(
              "flex items-center gap-2 px-6 py-2 rounded-full font-bold transition-all text-white",
              isAnalyzing 
                ? "bg-error/80 hover:bg-error shadow-[0_0_15px_rgba(255,180,171,0.4)]" 
                : "bg-primary text-surface hover:bg-primary-container neon-glow"
            )}
          >
            {isAnalyzing ? <StopCircle className="w-5 h-5" /> : <PlayCircle className="w-5 h-5" />}
            {isAnalyzing ? 'Zatrzymaj Analizę' : 'Rozpocznij'}
          </button>
        </div>
      </header>

      <div className="flex-1 grid grid-cols-1 lg:grid-cols-4 gap-6 min-h-0">
        {/* Main Video Area */}
        <div className="lg:col-span-3 glass-card rounded-2xl overflow-hidden relative border-white/10 flex flex-col">
          {/* Top Indicators HUD */}
          <div className="absolute top-4 left-4 right-4 flex justify-between items-start z-10">
            <div className="flex items-center gap-2 bg-black/50 backdrop-blur-md px-3 py-1.5 rounded-full border border-white/10">
              <div className={clsx("w-3 h-3 rounded-full", isAnalyzing ? "bg-red-500 ai-pulse" : "bg-gray-500")} />
              <span className="text-sm font-medium text-white">{isAnalyzing ? 'REC & ANALYZING' : 'STANDBY'}</span>
            </div>
            
            {errorMsg && (
              <div className="flex items-center gap-2 bg-error/20 text-error backdrop-blur-md px-4 py-2 rounded-lg border border-error/30 animate-pulse">
                <AlertTriangle className="w-5 h-5 shrink-0" />
                <span className="font-bold">{errorMsg}</span>
              </div>
            )}
          </div>

          <div className="flex-1 bg-black/40 flex items-center justify-center relative overflow-hidden">
            {isAnalyzing ? (
              isTestMode ? (
                <div className="w-full h-full flex items-center justify-center bg-surface-variant relative">
                  <span className="text-white/30 text-2xl font-bold tracking-widest uppercase">Video Feed Placeholder</span>
                  <div className="absolute inset-0 border-[4px] border-primary/20 m-8 rounded-xl border-dashed animate-pulse"></div>
                </div>
              ) : (
                <img 
                  src="http://localhost:8000/video_feed" 
                  alt="Live Video Stream" 
                  className="w-full h-full object-contain"
                />
              )
            ) : (
              <div className="flex flex-col items-center justify-center">
                <MonitorPlay className="w-24 h-24 text-white/10" />
                <p className="mt-4 text-on-surface-variant/50 text-sm">Oczekiwanie na uruchomienie strumienia...</p>
              </div>
            )}
          </div>
        </div>

        {/* Sidebar Metrics HUD */}
        <div className="flex flex-col gap-4 overflow-y-auto pr-2">
          {/* Angle Card */}
          <div className="glass-card p-5 rounded-2xl border-white/10">
            <h3 className="text-sm text-on-surface-variant font-medium mb-1">Kąt ugięcia kolan</h3>
            <div className="text-4xl font-bold text-white font-h1">{currentAngle}°</div>
            <div className="mt-4 h-2 bg-surface-variant rounded-full overflow-hidden">
              <div 
                className="h-full bg-primary transition-all duration-300"
                style={{ width: `${Math.min(100, (currentAngle / 180) * 100)}%` }}
              />
            </div>
            <p className="text-xs mt-2 text-on-surface-variant">Optymalnie: 90° - 120°</p>
          </div>
          
          {/* Score Card */}
          <div className="glass-card p-5 rounded-2xl border-white/10 flex flex-col items-center">
            <h3 className="text-sm text-on-surface-variant font-medium mb-4 w-full text-left">Skuteczność Odbicia</h3>
            <div className="relative w-32 h-32">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={pieData}
                    innerRadius={45}
                    outerRadius={60}
                    paddingAngle={2}
                    dataKey="value"
                    stroke="none"
                    animationDuration={500}
                  >
                    {pieData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                </PieChart>
              </ResponsiveContainer>
              <div className="absolute inset-0 flex items-center justify-center flex-col">
                <span className="text-2xl font-bold text-white">{score}%</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
