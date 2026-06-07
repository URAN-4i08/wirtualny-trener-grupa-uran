import { useCallback, useEffect, useRef, useState } from 'react';
import { useVoiceCommands } from '../context/VoiceCommandContext';
import { useAuth } from '../context/AuthContext';
import {
  AlertTriangle,
  Camera,
  CheckCircle2,
  MonitorPlay,
  PlayCircle,
  StopCircle,
  UploadCloud,
  WifiOff,
  Clock,
  Shield,
  Zap,
  ArrowRight,
  Footprints,
  Activity,
} from 'lucide-react';
import { clsx } from 'clsx';
import { PieChart, Pie, Cell, ResponsiveContainer } from 'recharts';
import { apiUrl, wsUrl } from '../config/api';
import { supabase } from '../config/supabase';

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
  // Pola biomechaniczne
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

function resolveAnalysisLabels(
  metrics: Metrics,
  isAnalyzing: boolean,
  cameraIndex: number,
  videoName: string | null,
) {
  const sourceLabel =
    metrics.source === 'camera' ? `Kamera ${cameraIndex + 1}` : videoName || 'Plik wideo';

  if (!isAnalyzing) {
    return { statusLabel: metrics.status, sourceLabel };
  }

  if (metrics.isContact) {
    return { statusLabel: 'Wykryto odbicie piłki', sourceLabel };
  }

  if (metrics.hasPose) {
    return {
      statusLabel: metrics.postureWarnings
        ? 'Popraw postawę — szczegóły w sekcji obok'
        : 'Analiza postawy — pozycja wygląda dobrze',
      sourceLabel,
    };
  }

  return { statusLabel: 'Czekam na sylwetkę w kadrze…', sourceLabel };
}

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
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    let reconnectTimer: number | undefined;
    let shouldReconnect = true;
    let ws: WebSocket | null = null;

    function connect() {
      ws = new WebSocket(wsUrl('/ws/metrics'));

      ws.onopen = () => {
        setConnectionError(null);
      };

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
        if (shouldReconnect) {
          reconnectTimer = window.setTimeout(connect, 2000);
        }
      };
    }

    connect();

    return () => {
      shouldReconnect = false;
      if (reconnectTimer) window.clearTimeout(reconnectTimer);
      ws?.close();
    };
  }, []);

  const score = Math.max(0, Math.min(100, metrics.score));
  const contactScore = metrics.contactScore ?? score;
  const { statusLabel, sourceLabel } = resolveAnalysisLabels(
    metrics,
    isAnalyzing,
    selectedCameraIndex,
    selectedVideoName,
  );
  const isFollowThrough = metrics.fazaRuchu === 'FOLLOW_THROUGH';
  const mainFeedback = (() => {
    if (!isAnalyzing) return metrics.postureWarnings || '—';
    if (!metrics.hasPose) return 'Stań w kadrze kamery, aby ocenić postawę';
    return metrics.postureWarnings || 'Pozycja wygląda dobrze';
  })();
  const contactFeedback = metrics.contactWarning || 'Czekam na odbicie piłki';
  const isPreparingVideo = metrics.source === 'file' && metrics.videoProcessingStatus === 'processing';
  const isVideoReady = metrics.source !== 'file' || metrics.videoProcessingStatus === 'ready';
  const canStartAnalysis = !isPreparingVideo && isVideoReady;
  const canStopAnalysis = isAnalyzing || isPreparingVideo;

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
        setConnectionError(`Nie udało się uruchomić kamery.`);
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

  const pieData = [
    { name: 'Punkty', value: score, color: '#4ade80' },
    { name: 'Brakujące', value: 100 - score, color: '#32353c' },
  ];

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
      status: mode === 'dual'
        ? 'Dual-Cam: frontowa + boczna'
        : `Kamera ${cameraIndex + 1} (${mode === 'side' ? 'boczna' : 'frontowa'})`,
      videoProcessingStatus: 'idle',
      videoProcessingProgress: 0,
    }));
    setFeedKey((current) => current + 1);
    setIsAnalyzing(false);
  }

  async function selectDualCamera() {
    setConnectionError(null);
    setSelectedVideoName(null);

    // 1. Najpierw zabij stary strumień — usuwa <img> z DOM, zrywając HTTP
    setIsAnalyzing(false);
    setCameraMode('dual');

    if (isAnalyzingRef.current) {
      try { await fetch(apiUrl('/api/analysis/stop'), { method: 'POST' }); } catch {}
    }

    // 2. Poczekaj aż stary generator na backendzie się zamknie i zwolni kamery
    await new Promise(r => setTimeout(r, 1500));

    // 3. Wyślij POST do backendu, żeby ustawić tryb camera_dual
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

    // 4. Ustaw metryki i uruchom nowy strumień
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
      if (!response.ok || !result.ok) {
        throw new Error(result.error || 'Nie udało się przesłać pliku.');
      }

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

  return (
    <div className="max-w-6xl mx-auto flex flex-col h-[calc(100vh-3rem)]">
      <header className="flex flex-col gap-4 mb-6 shrink-0 xl:flex-row xl:items-center xl:justify-between">
        <div>
          <h2 className="text-3xl font-bold text-white mb-2">Analiza Live</h2>
          <p className="text-on-surface-variant">Jedna kamera lub plik wideo z komputera, z podpowiedziami w czasie rzeczywistym.</p>
        </div>

        <div className="flex flex-col gap-4">
          <div className="flex flex-wrap gap-3">
          <button
            onClick={() => selectCamera(1, 'front')}
            className={clsx(
              'flex items-center gap-2 px-4 py-2 rounded-lg border transition',
              metrics.source === 'camera' && cameraMode === 'front'
                ? 'bg-primary/15 text-primary border-primary/30'
                : 'bg-surface-variant/50 text-white border-white/10 hover:bg-surface-variant',
            )}
          >
            <Camera className="w-4 h-4" />
            Kamera (Front — telefon)
          </button>

          <button
            onClick={() => selectCamera(0, 'side')}
            className={clsx(
              'flex items-center gap-2 px-4 py-2 rounded-lg border transition',
              metrics.source === 'camera' && cameraMode === 'side'
                ? 'bg-primary/15 text-primary border-primary/30'
                : 'bg-surface-variant/50 text-white border-white/10 hover:bg-surface-variant',
            )}
          >
            <Camera className="w-4 h-4" />
            Kamera (Bok — laptop)
          </button>

          <button
            onClick={selectDualCamera}
            className={clsx(
              'flex items-center gap-2 px-4 py-2 rounded-lg border transition',
              metrics.source === 'camera' && cameraMode === 'dual'
                ? 'bg-secondary/15 text-secondary border-secondary/30'
                : 'bg-surface-variant/50 text-white border-white/10 hover:bg-surface-variant',
            )}
          >
            <MonitorPlay className="w-4 h-4" />
            Dual-Cam
          </button>

          <input
            ref={fileInputRef}
            type="file"
            accept="video/mp4,video/quicktime,video/x-msvideo,video/x-matroska,video/webm"
            className="hidden"
            onChange={(event) => {
              const file = event.target.files?.[0];
              if (file) uploadVideo(file);
            }}
          />

          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={isUploading}
            className={clsx(
              'flex items-center gap-2 px-4 py-2 rounded-lg border transition',
              metrics.source === 'file'
                ? 'bg-secondary/15 text-secondary border-secondary/30'
                : 'bg-surface-variant/50 text-white border-white/10 hover:bg-surface-variant',
              isUploading && 'opacity-60 cursor-wait',
            )}
          >
            <UploadCloud className="w-4 h-4" />
            {isUploading ? 'Wgrywanie...' : 'Wideo z komputera'}
          </button>

          <button
            onClick={() => {
              if (canStopAnalysis) stopAnalysis();
              else startAnalysis();
            }}
            disabled={!canStartAnalysis && !canStopAnalysis}
            className={clsx(
              'flex items-center gap-2 px-6 py-2 rounded-full font-bold transition-all text-white',
              canStopAnalysis
                ? 'bg-error/80 hover:bg-error shadow-[0_0_15px_rgba(255,180,171,0.4)]'
                : 'bg-primary text-surface hover:bg-primary-container neon-glow',
              !canStartAnalysis && !canStopAnalysis && 'opacity-60 cursor-not-allowed',
            )}
          >
            {canStopAnalysis ? <StopCircle className="w-5 h-5" /> : <PlayCircle className="w-5 h-5" />}
            {canStopAnalysis ? 'Przerwij analizę' : 'Rozpocznij'}
          </button>
        </div>
        </div>
      </header>

      {connectionError && (
        <div className="mb-4 flex items-center gap-2 rounded-lg border border-error/30 bg-error/15 px-4 py-3 text-error">
          <WifiOff className="w-5 h-5 shrink-0" />
          <span className="font-medium">{connectionError}</span>
        </div>
      )}

      <div className="flex-1 grid grid-cols-1 lg:grid-cols-4 gap-6 min-h-0">
        <div className="lg:col-span-3 glass-card rounded-2xl overflow-hidden relative border-white/10 flex flex-col">
          <div className="absolute top-4 left-4 right-4 flex flex-col gap-3 z-10 md:flex-row md:justify-between md:items-start">
            <div className="flex items-center gap-2 bg-black/50 backdrop-blur-md px-3 py-1.5 rounded-full border border-white/10 w-fit">
              <div className={clsx('w-3 h-3 rounded-full', isAnalyzing ? 'bg-red-500 ai-pulse' : 'bg-gray-500')} />
              <span className="text-sm font-medium text-white">{isAnalyzing ? 'ANALIZA LIVE' : 'STANDBY'}</span>
            </div>

            {metrics.postureWarnings && (
              <div className="flex items-center gap-2 bg-error/20 text-error backdrop-blur-md px-4 py-2 rounded-lg border border-error/30">
                <AlertTriangle className="w-5 h-5 shrink-0" />
                <span className="font-bold">{metrics.postureWarnings}</span>
              </div>
            )}
          </div>

          <div className="flex-1 bg-black/40 flex items-center justify-center relative overflow-hidden">
            {isPreparingVideo ? (
              <div className="w-full max-w-md px-6 text-center">
                <UploadCloud className="w-16 h-16 text-primary mx-auto ai-pulse" />
                <p className="mt-4 text-white font-bold">Przygotowuję płynne odtwarzanie analizy</p>
                <div className="mt-5 h-3 bg-surface-variant rounded-full overflow-hidden">
                  <div
                    className="h-full bg-primary transition-all duration-300"
                    style={{ width: `${metrics.videoProcessingProgress}%` }}
                  />
                </div>
                <p className="mt-3 text-on-surface-variant text-sm">{metrics.videoProcessingProgress}%</p>
              </div>
            ) : isAnalyzing ? (
              <img
                src={`${apiUrl(cameraMode === 'dual' ? '/video_feed_dual' : '/video_feed')}?source=${metrics.source}&t=${feedKey}`}
                alt="Strumień analizy live"
                className="w-full h-full object-contain"
              />
            ) : (
              <div className="flex flex-col items-center justify-center px-6 text-center">
                <MonitorPlay className="w-24 h-24 text-white/10" />
                <p className="mt-4 text-on-surface-variant/70 text-sm">
                  Wybierz kamerę albo plik wideo, a potem rozpocznij analizę.
                </p>
              </div>
            )}
          </div>
        </div>

        {/* ── HUD: Panel informacyjny ──────────────────────────────────── */}
        <div className="flex flex-col gap-3 overflow-y-auto scrollbar-hide">

          {/* Gotowość do odbicia — 4 kwadraciki */}
          {metrics.gotowoscPrzedOdbiciem && (
            <div className="glass-card p-4 rounded-2xl border border-white/10">
              <p className="text-xs text-on-surface-variant font-medium mb-3">Pozycja przed odbiciem</p>
              <div className="grid grid-cols-4 gap-2">
                {[
                  { key: 'stopa_ok', label: 'Stopy', ok: metrics.gotowoscPrzedOdbiciem.stopa_ok },
                  { key: 'kolana_ok', label: 'Kolana', ok: metrics.gotowoscPrzedOdbiciem.kolana_ok },
                  { key: 'platforma_ok', label: 'Ręce', ok: metrics.gotowoscPrzedOdbiciem.platforma_ok },
                  { key: 'ruch_ok', label: 'Nogi', ok: metrics.gotowoscPrzedOdbiciem.ruch_ok },
                ].map((item) => (
                  <div key={item.key} className={clsx(
                    'flex flex-col items-center gap-1 p-2 rounded-lg transition-all',
                    item.ok ? 'bg-green-500/10' : 'bg-red-500/5',
                  )}>
                    <span className={clsx('text-base font-bold', item.ok ? 'text-green-400' : 'text-red-400/60')}>
                      {item.ok ? '✓' : '✗'}
                    </span>
                    <span className={clsx('text-xs', item.ok ? 'text-green-400/80' : 'text-red-400/40')}>
                      {item.label}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Wynik odbicia — prosty blok po kontakcie */}
          {isFollowThrough && metrics.feedbackFazy && (
            <div className={clsx(
              'glass-card p-4 rounded-2xl border contact-flash',
              metrics.feedbackFazy.includes('✓')
                ? 'border-green-500/30 bg-green-500/10'
                : 'border-red-500/20 bg-red-500/5',
            )}>
              <p className={clsx(
                'font-bold text-sm',
                metrics.feedbackFazy.includes('✓') ? 'text-green-400' : 'text-red-400',
              )}>
                {metrics.feedbackFazy}
              </p>
            </div>
          )}

          {/* Siatka 2-kolumnowa: Ocena + Kolana */}
          <div className="grid grid-cols-2 gap-3">
            {/* Skuteczność / PieChart */}
            <div className="glass-card p-4 rounded-2xl border border-white/10 flex flex-col items-center">
              <div className="relative w-20 h-20">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie data={pieData} innerRadius={25} outerRadius={35} paddingAngle={2} dataKey="value" stroke="none" animationDuration={500}>
                      {pieData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.color} />
                      ))}
                    </Pie>
                  </PieChart>
                </ResponsiveContainer>
                <div className="absolute inset-0 flex items-center justify-center">
                  <span className="text-lg font-bold text-white">{score}%</span>
                </div>
              </div>
              <p className="text-xs text-on-surface-variant mt-2">Skuteczność</p>
            </div>

            {/* Kąt kolan + odbicia */}
            <div className="glass-card p-4 rounded-2xl border border-white/10 flex flex-col justify-between">
              <div>
                <p className="text-xs text-on-surface-variant">Kolana</p>
                <p className="text-3xl font-bold text-white font-h1">{metrics.kneeAngle}°</p>
                <div className="w-full mt-2 h-1.5 bg-surface-variant rounded-full overflow-hidden">
                  <div
                    className="h-full bg-primary transition-all duration-300"
                    style={{ width: `${Math.min(100, (metrics.kneeAngle / 180) * 100)}%` }}
                  />
                </div>
              </div>
              <div className="mt-3 pt-3 border-t border-white/5">
                <p className="text-xs text-on-surface-variant">Odbicia</p>
                <p className="text-2xl font-bold text-white">{metrics.totalContacts}</p>
              </div>
            </div>
          </div>

          {/* Pasek fuzji (dual-cam) */}
          {cameraMode === 'dual' && metrics.fuzjaOcena !== undefined && (
            <div className="glass-card p-4 rounded-2xl border border-white/10">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs text-on-surface-variant font-medium">Fuzja obu kamer</span>
                <span className="text-sm text-white font-bold">{metrics.fuzjaOcena}/100</span>
              </div>
              <div className="h-2 bg-surface-variant rounded-full overflow-hidden">
                <div className="h-full bg-secondary transition-all duration-500 rounded-full" style={{ width: `${metrics.fuzjaOcena}%` }} />
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
