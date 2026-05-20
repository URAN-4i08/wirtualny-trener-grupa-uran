import { useEffect, useMemo, useState } from 'react';
import { AlertTriangle, Camera, CameraOff, FlaskConical, MonitorPlay, PlayCircle, StopCircle } from 'lucide-react';
import { clsx } from 'clsx';
import { Cell, Pie, PieChart, ResponsiveContainer } from 'recharts';

type CameraState = {
  enabled: boolean;
  index: number;
  status: string;
};

type LiveMetrics = {
  score?: number;
  kneeAngle?: number;
  elbowAngle?: number;
  warnings?: string | null;
  weakPoints?: string[];
  hitDetected?: boolean;
  lastHitMessage?: string;
  lastHitScore?: number;
  sideCamera?: CameraState;
  frontCamera?: CameraState;
};

const API_URL = 'http://localhost:8000';

export default function LiveAnalysis() {
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isTestMode, setIsTestMode] = useState(true);
  const [frontCameraEnabled, setFrontCameraEnabled] = useState(false);
  const [currentAngle, setCurrentAngle] = useState(120);
  const [elbowAngle, setElbowAngle] = useState(170);
  const [score, setScore] = useState(0);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [weakPoints, setWeakPoints] = useState<string[]>([]);
  const [hitDetected, setHitDetected] = useState(false);
  const [sideStatus, setSideStatus] = useState('Oczekiwanie');
  const [frontStatus, setFrontStatus] = useState('Wyłączona');

  useEffect(() => {
    if (!isAnalyzing) return;

    if (isTestMode) {
      const interval = setInterval(() => {
        const newAngle = 100 + Math.floor(Math.random() * 60);
        const newScore = Math.floor(Math.random() * 100);

        setCurrentAngle(newAngle);
        setElbowAngle(145 + Math.floor(Math.random() * 35));
        setScore(newScore);
        setHitDetected(Math.random() > 0.7);

        if (newAngle > 150) {
          setErrorMsg('Zbyt małe ugięcie kolan!');
          setWeakPoints(['Ugnij mocniej kolana przed przyjęciem']);
        } else if (newScore < 40) {
          setErrorMsg('Wyprostuj łokcie!');
          setWeakPoints(['Wyprostuj łokcie w momencie przyjęcia']);
        } else {
          setErrorMsg(null);
          setWeakPoints([]);
        }
      }, 1000);

      return () => clearInterval(interval);
    }

    const ws = new WebSocket('ws://localhost:8000/ws/metrics');

    ws.onmessage = (event) => {
      try {
        const data: LiveMetrics = JSON.parse(event.data);

        if (data.kneeAngle !== undefined) setCurrentAngle(data.kneeAngle);
        if (data.elbowAngle !== undefined) setElbowAngle(data.elbowAngle);
        if (data.score !== undefined) setScore(data.score);
        setErrorMsg(data.warnings || null);
        setWeakPoints(data.weakPoints || []);
        setHitDetected(Boolean(data.hitDetected));
        setSideStatus(data.sideCamera?.status || 'Oczekiwanie');
        setFrontStatus(data.frontCamera?.status || 'Wyłączona');
      } catch (err) {
        console.error('Błąd odczytu metryk WebSocket:', err);
      }
    };

    return () => ws.close();
  }, [isAnalyzing, isTestMode]);

  useEffect(() => {
    if (isTestMode || !isAnalyzing) return;

    fetch(`${API_URL}/api/camera/front`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ enabled: frontCameraEnabled }),
    }).catch((err) => {
      console.error('Nie udało się przełączyć kamery frontowej:', err);
    });
  }, [frontCameraEnabled, isAnalyzing, isTestMode]);

  const pieData = useMemo(() => [
    { name: 'Punkty', value: score, color: '#4ade80' },
    { name: 'Brakujące', value: Math.max(0, 100 - score), color: '#32353c' },
  ], [score]);

  const handleAnalysisToggle = () => {
    if (isAnalyzing && !isTestMode) {
      fetch(`${API_URL}/api/session/stop`, { method: 'POST' }).catch((err) => {
        console.error('Nie udało się zatrzymać sesji:', err);
      });
    }

    setIsAnalyzing(!isAnalyzing);
  };

  return (
    <div className="max-w-6xl mx-auto flex flex-col min-h-[calc(100vh-3rem)]">
      <header className="flex flex-col gap-4 mb-6 shrink-0 xl:flex-row xl:items-center xl:justify-between">
        <div>
          <h2 className="text-3xl font-bold text-white mb-2">Analiza Live</h2>
          <p className="text-on-surface-variant">
            Kamera 45° jest bazą analizy. Kamera frontowa może zostać dodana dla dokładniejszej oceny rąk.
          </p>
        </div>

        <div className="flex flex-wrap gap-3">
          <button
            onClick={() => setIsTestMode(!isTestMode)}
            className={clsx(
              'flex items-center gap-2 px-4 py-2 rounded-lg border transition',
              isTestMode
                ? 'bg-purple-500/20 text-purple-400 border-purple-500/30'
                : 'bg-surface-variant/50 text-on-surface-variant border-white/10 hover:bg-surface-variant',
            )}
            title="Tryb testowy bez podpinania backendu"
          >
            <FlaskConical className="w-4 h-4" />
            Tryb testowy
          </button>

          <button
            onClick={() => setFrontCameraEnabled(!frontCameraEnabled)}
            disabled={isTestMode}
            className={clsx(
              'flex items-center gap-2 px-4 py-2 rounded-lg border transition disabled:opacity-40 disabled:cursor-not-allowed',
              frontCameraEnabled
                ? 'bg-primary/20 text-primary border-primary/30'
                : 'bg-surface-variant/50 text-white border-white/10 hover:bg-surface-variant',
            )}
            title="Dodaj opcjonalną kamerę frontową"
          >
            {frontCameraEnabled ? <Camera className="w-4 h-4" /> : <CameraOff className="w-4 h-4" />}
            {frontCameraEnabled ? 'Front włączony' : 'Dodaj kamerę front'}
          </button>

          <button
            onClick={handleAnalysisToggle}
            className={clsx(
              'flex items-center gap-2 px-6 py-2 rounded-full font-bold transition-all text-white',
              isAnalyzing
                ? 'bg-error/80 hover:bg-error shadow-[0_0_15px_rgba(255,180,171,0.4)]'
                : 'bg-primary text-surface hover:bg-primary-container neon-glow',
            )}
          >
            {isAnalyzing ? <StopCircle className="w-5 h-5" /> : <PlayCircle className="w-5 h-5" />}
            {isAnalyzing ? 'Zatrzymaj analizę' : 'Rozpocznij'}
          </button>
        </div>
      </header>

      <div className="flex-1 grid grid-cols-1 lg:grid-cols-4 gap-6 min-h-0">
        <div className="lg:col-span-3 glass-card rounded-2xl overflow-hidden relative border-white/10 flex flex-col">
          <div className="absolute top-4 left-4 right-4 flex flex-wrap justify-between gap-3 items-start z-10">
            <div className="flex items-center gap-2 bg-black/50 backdrop-blur-md px-3 py-1.5 rounded-full border border-white/10">
              <div className={clsx('w-3 h-3 rounded-full', isAnalyzing ? 'bg-red-500 ai-pulse' : 'bg-gray-500')} />
              <span className="text-sm font-medium text-white">{isAnalyzing ? 'REC & ANALIZA' : 'GOTOWY'}</span>
            </div>

            {errorMsg && (
              <div className="flex items-center gap-2 bg-error/20 text-error backdrop-blur-md px-4 py-2 rounded-lg border border-error/30">
                <AlertTriangle className="w-5 h-5 shrink-0" />
                <span className="font-bold">{errorMsg}</span>
              </div>
            )}
          </div>

          <div className={clsx('flex-1 bg-black/40 grid gap-1 overflow-hidden', frontCameraEnabled && !isTestMode ? 'md:grid-cols-2' : 'grid-cols-1')}>
            {isAnalyzing ? (
              isTestMode ? (
                <div className="w-full min-h-[420px] flex items-center justify-center bg-surface-variant relative">
                  <span className="text-white/30 text-2xl font-bold tracking-widest uppercase">Video Feed Placeholder</span>
                  <div className="absolute inset-0 border-[4px] border-primary/20 m-8 rounded-xl border-dashed animate-pulse" />
                </div>
              ) : (
                <>
                  <VideoPanel title="Kamera 45°" status={sideStatus} src={`${API_URL}/video_feed/side`} />
                  {frontCameraEnabled && (
                    <VideoPanel title="Kamera frontowa" status={frontStatus} src={`${API_URL}/video_feed/front`} />
                  )}
                </>
              )
            ) : (
              <div className="min-h-[420px] flex flex-col items-center justify-center">
                <MonitorPlay className="w-24 h-24 text-white/10" />
                <p className="mt-4 text-on-surface-variant/50 text-sm">Oczekiwanie na uruchomienie strumienia...</p>
              </div>
            )}
          </div>
        </div>

        <aside className="flex flex-col gap-4 overflow-y-auto pr-2">
          <div className="glass-card p-5 rounded-2xl border-white/10">
            <h3 className="text-sm text-on-surface-variant font-medium mb-1">Kąt ugięcia kolan</h3>
            <div className="text-4xl font-bold text-white font-h1">{currentAngle}°</div>
            <MetricBar value={Math.min(100, (currentAngle / 180) * 100)} />
            <p className="text-xs mt-2 text-on-surface-variant">Optymalnie: 90° - 120°</p>
          </div>

          <div className="glass-card p-5 rounded-2xl border-white/10">
            <h3 className="text-sm text-on-surface-variant font-medium mb-1">Kąt łokci</h3>
            <div className="text-4xl font-bold text-white font-h1">{elbowAngle}°</div>
            <MetricBar value={Math.min(100, (elbowAngle / 180) * 100)} />
            <p className="text-xs mt-2 text-on-surface-variant">Ręce powinny być stabilne i wyprostowane</p>
          </div>

          <div className="glass-card p-5 rounded-2xl border-white/10 flex flex-col items-center">
            <h3 className="text-sm text-on-surface-variant font-medium mb-4 w-full text-left">Skuteczność przyjęcia</h3>
            <div className="relative w-32 h-32">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={pieData} innerRadius={45} outerRadius={60} paddingAngle={2} dataKey="value" stroke="none" animationDuration={500}>
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

          <div className="glass-card p-5 rounded-2xl border-white/10">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm text-on-surface-variant font-medium">Słabe punkty</h3>
              <span className={clsx('text-xs px-2 py-1 rounded-full', hitDetected ? 'bg-green-500/15 text-green-300' : 'bg-white/5 text-on-surface-variant')}>
                {hitDetected ? 'Odbicie' : 'Pozycja'}
              </span>
            </div>
            {weakPoints.length > 0 ? (
              <ul className="space-y-2">
                {weakPoints.map((point) => (
                  <li key={point} className="text-sm text-white/80 border-l-2 border-error/70 pl-3">
                    {point}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-on-surface-variant">Brak aktywnych uwag.</p>
            )}
          </div>
        </aside>
      </div>
    </div>
  );
}

function VideoPanel({ title, status, src }: { title: string; status: string; src: string }) {
  return (
    <div className="relative min-h-[420px] bg-black flex items-center justify-center">
      <img src={src} alt={title} className="w-full h-full object-contain" />
      <div className="absolute bottom-4 left-4 bg-black/55 backdrop-blur-md border border-white/10 rounded-lg px-3 py-2">
        <p className="text-sm font-bold text-white">{title}</p>
        <p className="text-xs text-on-surface-variant">{status}</p>
      </div>
    </div>
  );
}

function MetricBar({ value }: { value: number }) {
  return (
    <div className="mt-4 h-2 bg-surface-variant rounded-full overflow-hidden">
      <div className="h-full bg-primary transition-all duration-300" style={{ width: `${value}%` }} />
    </div>
  );
}
