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
        const url = `/api/source/camera?camera_index=${selectedCameraIndex}${user ? `&user_id=${user.id}` : ''}`;
        const response = await fetch(apiUrl(url), {
          method: 'POST',
          headers: await getSessionHeaders(),
        });
        if (!response.ok) throw new Error();
        setFeedKey((current) => current + 1);
      } catch {
        setConnectionError(`Nie udało się uruchomić kamery ${selectedCameraIndex + 1}.`);
        return;
      }
    }
    setIsAnalyzing(true);
  }, [metrics.source, selectedCameraIndex, user]);

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

  async function selectCamera(cameraIndex = 0) {
    setConnectionError(null);
    setSelectedVideoName(null);
    setSelectedCameraIndex(cameraIndex);
    if (isAnalyzingRef.current) {
      fetch(apiUrl('/api/analysis/stop'), { method: 'POST' }).catch(() => undefined);
    }
    setMetrics((current) => ({
      ...current,
      source: 'camera',
      status: `Wybrano kamerę ${cameraIndex + 1}`,
      videoProcessingStatus: 'idle',
      videoProcessingProgress: 0,
    }));
    setFeedKey((current) => current + 1);
    setIsAnalyzing(false);
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

        <div className="flex flex-wrap gap-3">
          <button
            onClick={() => selectCamera(0)}
            className={clsx(
              'flex items-center gap-2 px-4 py-2 rounded-lg border transition',
              metrics.source === 'camera' && selectedCameraIndex === 0
                ? 'bg-primary/15 text-primary border-primary/30'
                : 'bg-surface-variant/50 text-white border-white/10 hover:bg-surface-variant',
            )}
          >
            <Camera className="w-4 h-4" />
            Kamera 1
          </button>

          <button
            onClick={() => selectCamera(1)}
            className={clsx(
              'flex items-center gap-2 px-4 py-2 rounded-lg border transition',
              metrics.source === 'camera' && selectedCameraIndex === 1
                ? 'bg-primary/15 text-primary border-primary/30'
                : 'bg-surface-variant/50 text-white border-white/10 hover:bg-surface-variant',
            )}
          >
            <Camera className="w-4 h-4" />
            Kamera 2
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
                src={`${apiUrl('/video_feed')}?source=${metrics.source}&t=${feedKey}`}
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

        <div className="flex flex-col gap-4 overflow-y-auto pr-2">
          <div className="glass-card p-5 rounded-2xl border-white/10">
            <h3 className="text-sm text-on-surface-variant font-medium mb-1">Status</h3>
            <p className="text-white font-medium min-h-[1.5rem]">{statusLabel}</p>
            <p className="text-xs mt-2 text-on-surface-variant">Źródło: {sourceLabel}</p>
            {metrics.source === 'file' && (
              <p className="text-xs mt-2 text-on-surface-variant">
                Przygotowanie: {metrics.videoProcessingStatus === 'ready' ? 'gotowe' : `${metrics.videoProcessingProgress}%`}
              </p>
            )}
          </div>

          <div className="glass-card p-5 rounded-2xl border-white/10">
            <h3 className="text-sm text-on-surface-variant font-medium mb-1">Podpowiedź postawy</h3>
            <div className="mt-3 flex items-start gap-3">
              {metrics.postureWarnings ? (
                <AlertTriangle className="w-5 h-5 text-error shrink-0 mt-0.5" />
              ) : (
                <CheckCircle2 className="w-5 h-5 text-green-400 shrink-0 mt-0.5" />
              )}
              <p className={clsx('font-bold', metrics.postureWarnings ? 'text-error' : 'text-green-400')}>
                {mainFeedback}
              </p>
            </div>
          </div>

          <div className="glass-card p-5 rounded-2xl border-white/10">
            <h3 className="text-sm text-on-surface-variant font-medium mb-1">Ocena odbicia</h3>
            <div className="mb-3 rounded-lg border border-primary/20 bg-primary/10 p-3">
              <p className="text-xs text-on-surface-variant">Licznik odbić</p>
              <p className="text-4xl font-bold text-white">{metrics.totalContacts}</p>
            </div>
            <div className={clsx('mt-3 rounded-lg border p-3', metrics.isContact ? 'border-primary/40 bg-primary/10' : 'border-white/10 bg-surface-variant/30')}>
              <p className="text-white font-bold">{contactFeedback}</p>
              <p className="text-xs mt-2 text-on-surface-variant">
                {metrics.isContact ? `Wynik odbicia: ${contactScore}/100` : 'Komunikat pojawi się, gdy piłka będzie przy przedramionach.'}
              </p>
            </div>
          </div>

          <div className="glass-card p-5 rounded-2xl border-white/10">
            <h3 className="text-sm text-on-surface-variant font-medium mb-1">Kąt ugięcia kolan</h3>
            <div className="text-4xl font-bold text-white font-h1">{metrics.kneeAngle}°</div>
            <div className="mt-4 h-2 bg-surface-variant rounded-full overflow-hidden">
              <div
                className="h-full bg-primary transition-all duration-300"
                style={{ width: `${Math.min(100, (metrics.kneeAngle / 180) * 100)}%` }}
              />
            </div>
            <p className="text-xs mt-2 text-on-surface-variant">Optymalnie: 90° - 120°</p>
          </div>

          <div className="glass-card p-5 rounded-2xl border-white/10 flex flex-col items-center">
            <h3 className="text-sm text-on-surface-variant font-medium mb-4 w-full text-left">Skuteczność pozycji</h3>
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
        </div>
      </div>
    </div>
  );
}
