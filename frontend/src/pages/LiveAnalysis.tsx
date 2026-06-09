import { useCallback, useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { useVoiceCommands } from '../context/VoiceCommandContext';
import { useAuth } from '../context/AuthContext';
import {
  AlertTriangle,
  CheckCircle2,
  LayoutDashboard,
  MonitorPlay,
  UploadCloud,
  WifiOff,
  Clock,
  Info,
} from 'lucide-react';
import { clsx } from 'clsx';
import { PieChart, Pie, Cell, ResponsiveContainer } from 'recharts';
import { apiUrl, wsUrl } from '../config/api';
import { supabase } from '../config/supabase';
import PhaseStepper from '../components/live/PhaseStepper';
import ReadinessTiles from '../components/live/ReadinessTiles';
import FollowThroughOverlay from '../components/live/FollowThroughOverlay';

type Metrics = {
  score: number;
  kneeAngle: number;
  totalContacts: number;
  warnings: string | null;
  postureWarnings: string | null;
  contactWarning: string | null;
  contactScore: number | null;
  isContact: boolean;
  hasPose: boolean;
  hasBall: boolean;
  status: string;
  source: 'camera' | 'file';
  isAnalyzing: boolean;
  videoProcessingStatus: 'idle' | 'processing' | 'ready' | 'error';
  videoProcessingProgress: number;
  cameraMode?: 'front' | 'side' | 'dual';
  fuzjaOcena?: number;
  komunikatFuzji?: string | null;
  brakPracyNog?: boolean;
  typOdbicia?: 'DOLNE' | 'GORNE' | null;
  komunikatKolana?: string | null;
  zamachWykryty?: boolean;
  dynamikaZamachu?: string | null;
  dystansPilkaRece?: number | null;
  fazaRuchu?: 'OCZEKIWANIE' | 'PRZYGOTOWANIE' | 'KONTAKT' | 'FOLLOW_THROUGH';
  rozstawienieStop?: number | null;
  balansStop?: 'OK' | 'ZA_LEWO' | 'ZA_PRAWO' | null;
  gotowoscPrzedOdbiciem?: {
    stopa_ok: boolean;
    kolana_ok: boolean;
    platforma_ok: boolean;
    ruch_ok: boolean;
  } | null;
  feedbackFazy?: string | null;
  katBiodra?: number | null;
};

const initialMetrics: Metrics = {
  score: 0,
  kneeAngle: 120,
  totalContacts: 0,
  warnings: null,
  postureWarnings: null,
  contactWarning: null,
  contactScore: null,
  isContact: false,
  hasPose: false,
  hasBall: false,
  status: 'Oczekiwanie na uruchomienie analizy',
  source: 'camera',
  isAnalyzing: false,
  videoProcessingStatus: 'idle',
  videoProcessingProgress: 0,
};

function formatSessionTime(totalSeconds: number) {
  const h = Math.floor(totalSeconds / 3600).toString().padStart(2, '0');
  const m = Math.floor((totalSeconds % 3600) / 60).toString().padStart(2, '0');
  const s = (totalSeconds % 60).toString().padStart(2, '0');
  return `${h}:${m}:${s}`;
}

function footSpreadPercent(value: number | null | undefined) {
  if (value == null) return 50;
  const clamped = Math.max(0.6, Math.min(1.6, value));
  return Math.round(((clamped - 0.6) / 1.0) * 100);
}

export default function LiveAnalysis() {
  const { user } = useAuth();
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [metrics, setMetrics] = useState<Metrics>(initialMetrics);
  const [connectionError, setConnectionError] = useState<string | null>(null);
  const [selectedVideoName, setSelectedVideoName] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [feedKey, setFeedKey] = useState(0);
  const [selectedCameraIndex, setSelectedCameraIndex] = useState(0);
  const [cameraMode, setCameraMode] = useState<'front' | 'side' | 'dual'>('front');
  const [sessionSeconds, setSessionSeconds] = useState(0);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    let reconnectTimer: number | undefined;
    let shouldReconnect = true;
    let ws: WebSocket | null = null;

    function connect() {
      ws = new WebSocket(wsUrl('/ws/metrics'));
      ws.onopen = () => setConnectionError(null);
      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          setMetrics((current) => ({ ...current, ...data }));
          setConnectionError(null);
        } catch {
          setConnectionError('Nie udało się odczytać danych z analizy.');
        }
      };
      ws.onerror = () => {
        setConnectionError('Brak połączenia z serwerem analizy. Sprawdź, czy backend działa na porcie 8000.');
      };
      ws.onclose = () => {
        setMetrics((current) => ({ ...current, isAnalyzing: false }));
        if (shouldReconnect) reconnectTimer = window.setTimeout(connect, 2000);
      };
    }

    connect();
    return () => {
      shouldReconnect = false;
      if (reconnectTimer) window.clearTimeout(reconnectTimer);
      ws?.close();
    };
  }, []);

  useEffect(() => {
    if (!isAnalyzing) {
      setSessionSeconds(0);
      return;
    }
    const id = window.setInterval(() => setSessionSeconds((v) => v + 1), 1000);
    return () => window.clearInterval(id);
  }, [isAnalyzing]);

  const score = Math.max(0, Math.min(100, metrics.score));
  const contactScore = metrics.contactScore ?? score;
  const isFollowThrough = metrics.fazaRuchu === 'FOLLOW_THROUGH';
  const isPreparingVideo = metrics.source === 'file' && metrics.videoProcessingStatus === 'processing';
  const isVideoReady = metrics.source !== 'file' || metrics.videoProcessingStatus === 'ready';
  const canStartAnalysis = !isPreparingVideo && isVideoReady;
  const canStopAnalysis = isAnalyzing || isPreparingVideo;
  const showDualCamHint = !isAnalyzing && cameraMode !== 'dual';

  const coachBanner = (() => {
    if (isFollowThrough && metrics.feedbackFazy) return metrics.feedbackFazy;
    if (!isAnalyzing) return null;
    if (!metrics.hasPose) return 'Stań w kadrze kamery';
    if (metrics.postureWarnings) return metrics.postureWarnings;
    return 'Pozycja wygląda dobrze';
  })();

  const bannerPositive = coachBanner && !metrics.postureWarnings && metrics.hasPose;

  const isAnalyzingRef = useRef(isAnalyzing);
  const canStartAnalysisRef = useRef(canStartAnalysis);
  const { registerLiveHandlers } = useVoiceCommands();

  useEffect(() => {
    isAnalyzingRef.current = isAnalyzing;
  }, [isAnalyzing]);

  useEffect(() => {
    canStartAnalysisRef.current = canStartAnalysis;
  }, [canStartAnalysis]);

  const startAnalysis = useCallback(async () => {
    if (!canStartAnalysisRef.current && !isAnalyzingRef.current) return;
    if (metrics.source === 'camera') {
      try {
        let url: string;
        if (cameraMode === 'dual') {
          url = `/api/source/camera-dual?camera_index_a=1&camera_index_b=0${user ? `&user_id=${user.id}` : ''}`;
        } else {
          url = `/api/source/camera?camera_index=${selectedCameraIndex}&camera_mode=${cameraMode}${user ? `&user_id=${user.id}` : ''}`;
        }
        const response = await fetch(apiUrl(url), {
          method: 'POST',
          headers: await getSessionHeaders(),
        });
        if (!response.ok) throw new Error();
        setFeedKey((current) => current + 1);
      } catch {
        setConnectionError('Nie udało się uruchomić kamery.');
        return;
      }
    }
    setIsAnalyzing(true);
  }, [metrics.source, selectedCameraIndex, cameraMode, user]);

  const stopAnalysis = useCallback(() => {
    setIsAnalyzing(false);
    fetch(apiUrl('/api/analysis/stop'), { method: 'POST' }).catch(() => {
      setConnectionError('Nie udało się zatrzymać analizy na serwerze.');
    });
  }, []);

  useEffect(() => {
    registerLiveHandlers({ startAnalysis, stopAnalysis });
    return () => registerLiveHandlers(null);
  }, [registerLiveHandlers, startAnalysis, stopAnalysis]);

  async function getSessionHeaders() {
    const { data } = await supabase.auth.getSession();
    const token = data.session?.access_token;
    return token ? { Authorization: `Bearer ${token}` } : undefined;
  }

  async function selectCamera(cameraIndex = 0, mode: 'front' | 'side' = 'front') {
    setConnectionError(null);
    setSelectedVideoName(null);
    setSelectedCameraIndex(cameraIndex);
    setCameraMode(mode);
    if (isAnalyzingRef.current) {
      fetch(apiUrl('/api/analysis/stop'), { method: 'POST' }).catch(() => undefined);
    }
    setMetrics((current) => ({
      ...current,
      source: 'camera',
      status: `Kamera ${cameraIndex + 1}`,
      videoProcessingStatus: 'idle',
      videoProcessingProgress: 0,
    }));
    setFeedKey((current) => current + 1);
    setIsAnalyzing(false);
  }

  async function selectDualCamera() {
    setConnectionError(null);
    setSelectedVideoName(null);
    setIsAnalyzing(false);
    setCameraMode('dual');
    if (isAnalyzingRef.current) {
      try {
        await fetch(apiUrl('/api/analysis/stop'), { method: 'POST' });
      } catch {
        /* ignore */
      }
    }
    await new Promise((r) => window.setTimeout(r, 1500));
    try {
      const url = `/api/source/camera-dual?camera_index_a=1&camera_index_b=0${user ? `&user_id=${user.id}` : ''}`;
      const response = await fetch(apiUrl(url), {
        method: 'POST',
        headers: await getSessionHeaders(),
      });
      if (!response.ok) throw new Error();
    } catch {
      setConnectionError('Nie udało się uruchomić Dual-Cam.');
      return;
    }
    setMetrics((current) => ({
      ...current,
      source: 'camera',
      cameraMode: 'dual',
      status: 'Dual-Cam: synchronizacja kamer...',
      videoProcessingStatus: 'idle',
      videoProcessingProgress: 0,
    }));
    setFeedKey((current) => current + 1);
    setIsAnalyzing(true);
  }

  async function uploadVideo(file: File) {
    setConnectionError(null);
    setIsUploading(true);
    setIsAnalyzing(false);
    const formData = new FormData();
    formData.append('file', file);
    try {
      const url = `/api/source/upload${user ? `?user_id=${user.id}` : ''}`;
      const response = await fetch(apiUrl(url), {
        method: 'POST',
        headers: await getSessionHeaders(),
        body: formData,
      });
      const result = await response.json();
      if (!response.ok || !result.ok) throw new Error(result.error || 'Upload failed');
      setSelectedVideoName(result.videoName || file.name);
      setMetrics((current) => ({
        ...current,
        source: 'file',
        status: `Przygotowuję analizę pliku: ${result.videoName || file.name}`,
        videoProcessingStatus: 'processing',
        videoProcessingProgress: 0,
      }));
      setFeedKey((current) => current + 1);
    } catch (error) {
      setConnectionError(error instanceof Error ? error.message : 'Nie udało się przesłać pliku wideo.');
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  }

  const pieData = [
    { name: 'Punkty', value: score, color: '#f97316' },
    { name: 'Brak', value: 100 - score, color: '#352720' },
  ];

  const sourceButtons = [
    { id: 'front', label: 'Kamera front', action: () => void selectCamera(1, 'front'), active: metrics.source === 'camera' && cameraMode === 'front' },
    { id: 'side', label: 'Kamera bok', action: () => void selectCamera(0, 'side'), active: metrics.source === 'camera' && cameraMode === 'side' },
    { id: 'dual', label: 'Dual-Cam', action: () => void selectDualCamera(), active: metrics.source === 'camera' && cameraMode === 'dual' },
    { id: 'file', label: 'Plik', action: () => fileInputRef.current?.click(), active: metrics.source === 'file' },
  ] as const;

  return (
    <div className="flex min-h-screen flex-col bg-navy">
      <header className="glass-panel sticky top-0 z-30 flex h-16 shrink-0 items-center justify-between gap-4 border-b border-white/10 px-4 md:px-6">
        <div className="flex items-center gap-4">
          <Link to="/dashboard" className="rounded-lg p-2 text-on-surface-variant hover:bg-white/5 hover:text-on-surface" title="Panel główny">
            <LayoutDashboard className="h-5 w-5" />
          </Link>
          <div>
            <h1 className="font-display text-lg font-semibold text-on-surface">Analiza na żywo</h1>
            <p className="hidden text-xs text-on-surface-variant sm:block">Odbicie dolne — feedback w czasie rzeczywistym</p>
          </div>
          <div className="hidden items-center gap-2 sm:flex">
            <span className={clsx('flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-semibold', isAnalyzing ? 'border-success/30 bg-success/10 text-success' : 'border-white/10 bg-white/5 text-on-surface-variant')}>
              <span className={clsx('h-2 w-2 rounded-full', isAnalyzing ? 'bg-success pulse-live' : 'bg-outline')} />
              {isAnalyzing ? 'Połączono' : 'Standby'}
            </span>
            {isAnalyzing && (
              <span className="flex items-center gap-1.5 rounded-full border border-white/10 bg-white/5 px-2.5 py-1 font-mono text-xs text-on-surface-variant">
                <Clock className="h-3.5 w-3.5" />
                {formatSessionTime(sessionSeconds)}
              </span>
            )}
          </div>
        </div>

        <div className="flex items-center gap-2">
          <div className="hidden rounded-lg bg-surface-container p-1 md:flex">
            {sourceButtons.map((btn) => (
              <button
                key={btn.id}
                type="button"
                onClick={btn.action}
                disabled={btn.id === 'file' && isUploading}
                className={clsx(
                  'rounded-md px-3 py-1.5 text-xs font-semibold transition-all',
                  btn.active ? 'bg-white/10 text-on-surface' : 'text-on-surface-variant hover:bg-white/5',
                )}
              >
                {btn.id === 'file' && isUploading ? 'Wgrywanie...' : btn.label}
              </button>
            ))}
          </div>
          <button
            type="button"
            onClick={() => (canStopAnalysis ? stopAnalysis() : startAnalysis())}
            disabled={!canStartAnalysis && !canStopAnalysis}
            className={clsx(
              'rounded-xl px-5 py-2.5 text-sm font-bold transition-all',
              canStopAnalysis ? 'bg-error/90 text-white hover:bg-error' : 'bg-primary-container text-on-primary-container hover:brightness-110',
              !canStartAnalysis && !canStopAnalysis && 'cursor-not-allowed opacity-50',
            )}
          >
            {canStopAnalysis ? 'Przerwij' : 'Rozpocznij'}
          </button>
        </div>
      </header>

      <input
        ref={fileInputRef}
        type="file"
        accept="video/mp4,video/quicktime,video/x-msvideo,video/x-matroska,video/webm"
        className="hidden"
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) void uploadVideo(file);
        }}
      />

      {connectionError && (
        <div className="mx-4 mt-4 flex items-center gap-2 rounded-xl border border-error/30 bg-error/10 px-4 py-3 text-error md:mx-6">
          <WifiOff className="h-5 w-5 shrink-0" />
          <span className="text-sm font-medium">{connectionError}</span>
        </div>
      )}

      {showDualCamHint && (
        <div className="mx-4 mt-4 flex items-start gap-3 rounded-xl border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-amber-100 md:mx-6">
          <Info className="mt-0.5 h-5 w-5 shrink-0" />
          <p className="text-sm">
            <strong>Wskazówka:</strong> Podłącz telefon i wybierz <strong>Dual-Cam</strong> — dokładniejsza ocena ugięcia kolan.
          </p>
        </div>
      )}

      <main className="grid flex-1 grid-cols-1 gap-4 p-4 lg:grid-cols-12 lg:p-6">
        <div className="flex flex-col gap-4 lg:col-span-9">
          <PhaseStepper current={metrics.fazaRuchu ?? 'OCZEKIWANIE'} />

          <div className="relative aspect-video overflow-hidden rounded-2xl border border-white/10 bg-surface-container-high">
            {isPreparingVideo ? (
              <div className="flex h-full flex-col items-center justify-center px-6 text-center">
                <UploadCloud className="h-16 w-16 text-primary pulse-orange" />
                <p className="mt-4 font-display text-lg font-bold text-on-surface">Przygotowuję analizę wideo</p>
                <div className="mt-5 h-2 w-full max-w-xs overflow-hidden rounded-full bg-white/10">
                  <div className="h-full bg-primary-container transition-all" style={{ width: `${metrics.videoProcessingProgress}%` }} />
                </div>
                <p className="mt-2 text-sm text-on-surface-variant">{metrics.videoProcessingProgress}%</p>
              </div>
            ) : isAnalyzing ? (
              <>
                <img
                  src={`${apiUrl(cameraMode === 'dual' ? '/video_feed_dual' : '/video_feed')}?source=${metrics.source}&t=${feedKey}`}
                  alt="Strumień analizy"
                  className="h-full w-full object-contain"
                />
                {isFollowThrough && metrics.feedbackFazy && (
                  <FollowThroughOverlay
                    feedback={metrics.feedbackFazy}
                    score={contactScore}
                    gotowosc={metrics.gotowoscPrzedOdbiciem}
                    postureWarnings={metrics.postureWarnings}
                  />
                )}
              </>
            ) : (
              <div className="flex h-full flex-col items-center justify-center text-center">
                <MonitorPlay className="h-20 w-20 text-white/15" />
                <p className="mt-4 text-on-surface-variant">Wybierz źródło i kliknij Rozpocznij</p>
                {selectedVideoName && metrics.source === 'file' && (
                  <p className="mt-2 text-sm text-primary-container">Plik: {selectedVideoName}</p>
                )}
              </div>
            )}

            {isAnalyzing && !isFollowThrough && (
              <>
                <div className="absolute left-4 top-4 flex items-center gap-2 rounded-lg bg-red-600 px-3 py-1.5 shadow-lg">
                  <span className="h-2.5 w-2.5 animate-pulse rounded-full bg-white" />
                  <span className="text-xs font-bold uppercase tracking-widest text-white">Live</span>
                </div>

                {coachBanner && (
                  <div
                    className={clsx(
                      'absolute left-1/2 top-4 max-w-[90%] -translate-x-1/2 rounded-full border px-5 py-2.5 shadow-lg backdrop-blur-md',
                      bannerPositive
                        ? 'border-success/40 bg-success/20 text-green-100'
                        : 'border-primary-container/50 bg-primary-container/25 text-on-surface',
                    )}
                  >
                    <div className="flex items-center gap-2">
                      {bannerPositive ? (
                        <CheckCircle2 className="h-5 w-5 shrink-0 text-success" />
                      ) : (
                        <AlertTriangle className="h-5 w-5 shrink-0 text-primary" />
                      )}
                      <span className="font-display text-base font-bold md:text-lg">{coachBanner}</span>
                    </div>
                  </div>
                )}

                <div className="absolute bottom-4 left-4 flex flex-wrap items-center gap-4 rounded-xl glass-panel p-4">
                  <div>
                    <p className="text-xs font-semibold uppercase text-on-surface-variant">Rozstaw stóp</p>
                    <div className="mt-1 flex items-center gap-2">
                      <div className="h-2 w-32 overflow-hidden rounded-full bg-white/10">
                        <div className="h-full bg-primary" style={{ width: `${footSpreadPercent(metrics.rozstawienieStop)}%` }} />
                      </div>
                      <span className="text-sm font-bold text-on-surface">
                        {metrics.rozstawienieStop != null ? metrics.rozstawienieStop.toFixed(2) : '—'}
                      </span>
                    </div>
                  </div>
                  <div className="h-10 w-px bg-white/10" />
                  <div>
                    <p className="text-xs font-semibold uppercase text-on-surface-variant">Odbicia</p>
                    <p className="font-display text-2xl font-bold text-primary-container">{metrics.totalContacts}</p>
                  </div>
                </div>
              </>
            )}
          </div>

          <div className="flex gap-2 overflow-x-auto md:hidden">
            {sourceButtons.map((btn) => (
              <button
                key={btn.id}
                type="button"
                onClick={btn.action}
                className={clsx(
                  'shrink-0 rounded-lg border px-3 py-2 text-xs font-semibold',
                  btn.active ? 'border-primary bg-primary/10 text-primary' : 'border-white/10 text-on-surface-variant',
                )}
              >
                {btn.label}
              </button>
            ))}
          </div>
        </div>

        <aside className="flex flex-col gap-4 lg:col-span-3">
          <div className="glass-card rounded-2xl p-5">
            <ReadinessTiles gotowosc={metrics.gotowoscPrzedOdbiciem} postureWarnings={metrics.postureWarnings} />
          </div>

          <div className="glass-card rounded-2xl p-5 text-center">
            <p className="text-xs font-semibold uppercase tracking-wide text-on-surface-variant">Efektywność sesji</p>
            <div className="relative mx-auto my-4 h-36 w-36">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={pieData} innerRadius={48} outerRadius={62} dataKey="value" stroke="none">
                    {pieData.map((entry, i) => (
                      <Cell key={i} fill={entry.color} />
                    ))}
                  </Pie>
                </PieChart>
              </ResponsiveContainer>
              <div className="absolute inset-0 flex items-center justify-center">
                <span className="font-display text-3xl font-bold">{score}%</span>
              </div>
            </div>
          </div>

          <div className="glass-card rounded-2xl p-5">
            <p className="text-xs font-semibold uppercase text-on-surface-variant">Kąt kolan</p>
            <p className="font-display text-4xl font-bold text-primary-container">{metrics.kneeAngle}°</p>
            <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-white/10">
              <div className="h-full bg-secondary transition-all" style={{ width: `${Math.min(100, (metrics.kneeAngle / 180) * 100)}%` }} />
            </div>
          </div>

          {cameraMode === 'dual' && metrics.fuzjaOcena !== undefined && (
            <div className="glass-card rounded-2xl p-5">
              <div className="mb-2 flex justify-between text-sm">
                <span className="text-on-surface-variant">Fuzja kamer</span>
                <span className="font-bold text-on-surface">{metrics.fuzjaOcena}/100</span>
              </div>
              <div className="h-2 overflow-hidden rounded-full bg-white/10">
                <div className="h-full bg-secondary transition-all" style={{ width: `${metrics.fuzjaOcena}%` }} />
              </div>
            </div>
          )}

          {!isFollowThrough && metrics.feedbackFazy && isAnalyzing && (
            <div className="glass-card rounded-2xl border border-white/10 p-4 text-sm text-on-surface-variant">{metrics.feedbackFazy}</div>
          )}
        </aside>
      </main>
    </div>
  );
}
