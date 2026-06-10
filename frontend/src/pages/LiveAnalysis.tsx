import { useCallback, useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { useVoiceCommands } from '../context/VoiceCommandContext';
import { useAuth } from '../context/AuthContext';
import {
  AlertTriangle,
  ArrowLeftRight,
  CheckCircle2,
  LayoutDashboard,
  Mic,
  MicOff,
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
import SessionSetupOverlay from '../components/live/SessionSetupOverlay';
import SessionTimerOverlay from '../components/live/SessionTimerOverlay';
import SessionSummaryOverlay from '../components/live/SessionSummaryOverlay';
import VoiceCommandBubble from '../components/voice/VoiceCommandBubble';
import { playCountdownTick, playSessionEnd, playSessionStart } from '../lib/countdownSound';
import { deriveElbowOk } from '../lib/elementScores';

type SessionSummary = {
  count: number;
  avgScore: number;
  bestScore: number;
  feedback: string;
  gotowosc?: {
    stopa_ok: boolean;
    kolana_ok: boolean;
    platforma_ok: boolean;
    lokcie_ok?: boolean;
    ruch_ok: boolean;
  } | null;
};

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
  hasLegs?: boolean;
  komunikatNogi?: string | null;
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
    lokcie_ok?: boolean;
    ruch_ok: boolean;
  } | null;
  feedbackFazy?: string | null;
  katBiodra?: number | null;
  sessionStatus?: 'idle' | 'setup' | 'prep' | 'active' | 'summary';
  sessionSecondsRemaining?: number;
  sessionContactCount?: number;
  sessionSummary?: SessionSummary | null;
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
  hasLegs: false,
  komunikatNogi: null,
  hasBall: false,
  status: 'Oczekiwanie na uruchomienie analizy',
  source: 'camera',
  isAnalyzing: false,
  videoProcessingStatus: 'idle',
  videoProcessingProgress: 0,
  sessionStatus: 'idle',
  sessionSecondsRemaining: 0,
  sessionContactCount: 0,
  sessionSummary: null,
};

function formatSessionTime(totalSeconds: number) {
  const h = Math.floor(totalSeconds / 3600).toString().padStart(2, '0');
  const m = Math.floor((totalSeconds % 3600) / 60).toString().padStart(2, '0');
  const s = (totalSeconds % 60).toString().padStart(2, '0');
  return `${h}:${m}:${s}`;
}

function footSpreadPercent(value: number | null | undefined) {
  if (value == null) return 50;
  const clamped = Math.max(0.65, Math.min(1.55, value));
  return Math.round(((clamped - 0.65) / 0.9) * 100);
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
  const [dualCamIndices, setDualCamIndices] = useState({ front: 0, side: 1 });
  const [availableCameras, setAvailableCameras] = useState<number[]>([0]);
  const [isSwappingCameras, setIsSwappingCameras] = useState(false);
  const [sessionSeconds, setSessionSeconds] = useState(0);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const lastTickSecondRef = useRef<number | null>(null);
  const lastSessionPhaseRef = useRef<string>('idle');
  const isAnalyzingRef = useRef(isAnalyzing);
  const selectedVideoNameRef = useRef<string | null>(null);

  useEffect(() => {
    void refreshCameraList();
  }, []);

  async function refreshCameraList(force = false): Promise<number[]> {
    try {
      const response = await fetch(apiUrl(`/api/cameras${force ? '?refresh=1' : ''}`));
      const data = await response.json();
      const cameras: number[] = Array.isArray(data.cameras) ? data.cameras : [];
      if (cameras.length > 0) {
        setAvailableCameras(cameras);
      }
      if (cameras.length >= 2) {
        setDualCamIndices({ front: cameras[0], side: cameras[1] });
      } else if (cameras.length === 1) {
        setDualCamIndices({ front: cameras[0], side: 1 });
      }
      return cameras;
    } catch {
      return availableCameras;
    }
  }

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
          setMetrics((current) => {
            const merged = { ...current, ...data };
            // Nie pozwól starym metrykom z pliku wideo zasłonić aktywnego strumienia kamery.
            if (isAnalyzingRef.current && !selectedVideoNameRef.current) {
              merged.source = 'camera';
              merged.videoProcessingStatus = 'idle';
              merged.videoProcessingProgress = 0;
            }
            return merged;
          });
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
  const sessionStatus = metrics.sessionStatus ?? 'idle';
  const isSessionSummary = sessionStatus === 'summary' && Boolean(metrics.sessionSummary);
  const isFollowThrough =
    !isSessionSummary && sessionStatus !== 'idle' && metrics.fazaRuchu === 'FOLLOW_THROUGH';
  const showSessionSetup = isAnalyzing && sessionStatus === 'setup';
  const inTimedTrial = sessionStatus === 'setup' || sessionStatus === 'prep' || sessionStatus === 'active';
  const setupAlmostReady =
    showSessionSetup &&
    metrics.hasPose &&
    metrics.hasLegs &&
    Boolean(metrics.gotowoscPrzedOdbiciem?.stopa_ok) &&
    Boolean(metrics.gotowoscPrzedOdbiciem?.kolana_ok) &&
    Boolean(metrics.gotowoscPrzedOdbiciem?.platforma_ok) &&
    Boolean(metrics.gotowoscPrzedOdbiciem?.ruch_ok) &&
    (metrics.gotowoscPrzedOdbiciem?.lokcie_ok !== undefined
      ? Boolean(metrics.gotowoscPrzedOdbiciem?.lokcie_ok)
      : deriveElbowOk(metrics.postureWarnings));
  const showSessionTimer = isAnalyzing && (sessionStatus === 'prep' || sessionStatus === 'active');
  const hideCoachBanner =
    showSessionTimer || isSessionSummary || showSessionSetup || sessionStatus === 'idle';
  const isPreparingVideo =
    metrics.source === 'file' &&
    metrics.videoProcessingStatus === 'processing' &&
    Boolean(selectedVideoName);
  const isVideoReady = metrics.source !== 'file' || metrics.videoProcessingStatus === 'ready';
  const canStartTrial =
    isAnalyzing &&
    metrics.source === 'camera' &&
    !inTimedTrial &&
    sessionStatus !== 'summary' &&
    isVideoReady &&
    !isPreparingVideo;
  const canCancelTrial = inTimedTrial;
  const showDualCamHint = isAnalyzing && cameraMode !== 'dual' && sessionStatus === 'idle';

  const coachBanner = (() => {
    if (sessionStatus === 'idle' || isSessionSummary) return null;
    if (isFollowThrough && metrics.feedbackFazy) return metrics.feedbackFazy;
    if (!isAnalyzing) return null;
    if (!metrics.hasPose) return 'Stań w kadrze kamery';
    if (metrics.komunikatNogi) return metrics.komunikatNogi;
    if (metrics.postureWarnings) return metrics.postureWarnings;
    return 'Pozycja wygląda dobrze';
  })();

  const bannerPositive = coachBanner && metrics.hasPose && metrics.hasLegs && !metrics.postureWarnings && !metrics.komunikatNogi;

  const cameraCoachTip = (() => {
    if (sessionStatus === 'idle' || isSessionSummary || isFollowThrough) return null;
    if (!hideCoachBanner && coachBanner) {
      return { text: coachBanner, positive: Boolean(bannerPositive) };
    }
    if (inTimedTrial && metrics.feedbackFazy) {
      return { text: metrics.feedbackFazy, positive: metrics.feedbackFazy.includes('✓') };
    }
    return null;
  })();

  const canStartTrialRef = useRef(canStartTrial);
  const {
    registerLiveHandlers,
    heardText,
    lastCommand,
    isListening,
    enabled: voiceEnabled,
    activateVoice,
    deactivateVoice,
    isActivating: voiceActivating,
    isSupported: voiceSupported,
  } = useVoiceCommands();

  useEffect(() => {
    isAnalyzingRef.current = isAnalyzing;
  }, [isAnalyzing]);

  useEffect(() => {
    selectedVideoNameRef.current = selectedVideoName;
  }, [selectedVideoName]);

  useEffect(() => {
    canStartTrialRef.current = canStartTrial;
  }, [canStartTrial]);

  useEffect(() => {
    const phase = metrics.sessionStatus ?? 'idle';
    const sec = metrics.sessionSecondsRemaining ?? 0;

    if (phase === 'prep' && lastSessionPhaseRef.current === 'setup') {
      playCountdownTick();
    }
    if (phase === 'active' && lastSessionPhaseRef.current === 'prep') {
      playSessionStart();
    }
    if (phase === 'summary' && lastSessionPhaseRef.current === 'active') {
      playSessionEnd();
    }
    lastSessionPhaseRef.current = phase;

    if ((phase === 'prep' || phase === 'active') && sec > 0) {
      if (lastTickSecondRef.current !== sec) {
        lastTickSecondRef.current = sec;
        playCountdownTick({ urgent: phase === 'active' && sec <= 3 });
      }
    } else {
      lastTickSecondRef.current = null;
    }
  }, [metrics.sessionStatus, metrics.sessionSecondsRemaining]);

  async function getSessionHeaders() {
    const { data } = await supabase.auth.getSession();
    const token = data.session?.access_token;
    return token ? { Authorization: `Bearer ${token}` } : undefined;
  }

  async function beginTimedSession() {
    if (metrics.source !== 'camera') return;
    await fetch(apiUrl('/api/session/start'), { method: 'POST' }).catch(() => undefined);
  }

  const openCameraStream = useCallback(
    async (overrides?: { cameraIndex?: number; mode?: 'front' | 'side' | 'dual'; dualIndices?: { front: number; side: number } }) => {
      const mode = overrides?.mode ?? cameraMode;
      const index = overrides?.cameraIndex ?? selectedCameraIndex;
      const dual = overrides?.dualIndices ?? dualCamIndices;
      try {
        let url: string;
        if (mode === 'dual') {
          url = `/api/source/camera-dual?camera_index_a=${dual.front}&camera_index_b=${dual.side}${user ? `&user_id=${user.id}` : ''}`;
        } else {
          url = `/api/source/camera?camera_index=${index}&camera_mode=${mode}${user ? `&user_id=${user.id}` : ''}`;
        }
        const response = await fetch(apiUrl(url), {
          method: 'POST',
          headers: await getSessionHeaders(),
        });
        if (!response.ok) {
          const result = await response.json().catch(() => ({}));
          const available = Array.isArray(result.availableCameras) ? result.availableCameras.join(', ') : '';
          const baseMessage = result.error || 'Nie udało się uruchomić kamery.';
          throw new Error(available ? `${baseMessage} (wykryte: ${available})` : baseMessage);
        }
        let resolvedDual = dual;
        if (mode === 'dual') {
          const result = await response.json();
          if (result.cameraIndex != null && result.cameraIndex2 != null) {
            resolvedDual = { front: result.cameraIndex, side: result.cameraIndex2 };
            setDualCamIndices(resolvedDual);
          }
        }
        setSelectedVideoName(null);
        setCameraMode(mode === 'dual' ? 'dual' : mode);
        if (mode !== 'dual') {
          setSelectedCameraIndex(index);
        }
        setMetrics((current) => ({
          ...current,
          source: 'camera',
          cameraMode: mode === 'dual' ? 'dual' : mode,
          status:
            mode === 'dual'
              ? `Dual-Cam: front (${resolvedDual.front}) + bok (${resolvedDual.side})`
              : `Kamera ${index + 1}`,
          videoProcessingStatus: 'idle',
          videoProcessingProgress: 0,
        }));
        setFeedKey((current) => current + 1);
        return true;
      } catch (error) {
        setConnectionError(error instanceof Error ? error.message : 'Nie udało się uruchomić kamery.');
        return false;
      }
    },
    [selectedCameraIndex, cameraMode, dualCamIndices, user],
  );

  const startTrial = useCallback(async () => {
    if (metrics.source !== 'camera') return;
    if (!isAnalyzingRef.current) {
      const ok = await openCameraStream();
      if (!ok) return;
      setIsAnalyzing(true);
    }
    await beginTimedSession();
  }, [metrics.source, openCameraStream]);

  const cancelTrial = useCallback(async () => {
    await fetch(apiUrl('/api/session/stop'), { method: 'POST' }).catch(() => undefined);
  }, []);

  const stopCameraStream = useCallback(() => {
    setIsAnalyzing(false);
    fetch(apiUrl('/api/analysis/stop'), { method: 'POST' }).catch(() => {
      setConnectionError('Nie udało się zatrzymać kamery.');
    });
  }, []);

  const openCameraStreamRef = useRef(openCameraStream);
  useEffect(() => {
    openCameraStreamRef.current = openCameraStream;
  }, [openCameraStream]);

  useEffect(() => {
    let cancelled = false;
    let retryTimer: number | undefined;

    async function bootstrapCamera(attempt = 0) {
      const ok = await openCameraStreamRef.current();
      if (cancelled) return;
      if (ok) {
        setIsAnalyzing(true);
        return;
      }
      if (attempt < 4) {
        retryTimer = window.setTimeout(() => void bootstrapCamera(attempt + 1), 1500);
      }
    }

    void bootstrapCamera();
    return () => {
      cancelled = true;
      if (retryTimer) window.clearTimeout(retryTimer);
    };
  }, []);

  const canCancelTrialRef = useRef(canCancelTrial);

  useEffect(() => {
    canCancelTrialRef.current = canCancelTrial;
  }, [canCancelTrial]);

  const stopAnalysis = useCallback(async () => {
    if (canCancelTrialRef.current) {
      await cancelTrial();
    }
    // Kamera zostaje włączona w trybie idle — zatrzymujemy ją tylko przy przejściu na plik.
  }, [cancelTrial]);

  const startAnalysis = useCallback(async () => {
    if (metrics.source === 'camera') {
      await startTrial();
      return;
    }
    if (canStartTrialRef.current || isVideoReady) {
      setIsAnalyzing(true);
    }
  }, [metrics.source, startTrial, isVideoReady]);

  useEffect(() => {
    registerLiveHandlers({ startAnalysis, stopAnalysis });
    return () => registerLiveHandlers(null);
  }, [registerLiveHandlers, startAnalysis, stopAnalysis]);

  async function selectCamera(cameraIndex = 0, mode: 'front' | 'side' = 'front') {
    setConnectionError(null);
    setSelectedVideoName(null);
    await fetch(apiUrl('/api/session/stop'), { method: 'POST' }).catch(() => undefined);
    const ok = await openCameraStream({ cameraIndex, mode });
    if (ok) setIsAnalyzing(true);
  }

  async function configureDualCamera(indices = dualCamIndices, restartStream = true) {
    setConnectionError(null);
    setSelectedVideoName(null);

    const cameras = await refreshCameraList(true);

    const dualIndices =
      indices.front !== indices.side && cameras.includes(indices.front) && cameras.includes(indices.side)
        ? indices
        : cameras.length >= 2
          ? { front: cameras[0], side: cameras[1] }
          : { front: 0, side: 1 };
    setDualCamIndices(dualIndices);
    const fallbackMode: 'front' | 'side' = cameraMode === 'side' ? 'side' : 'front';
    const fallbackIndex = selectedCameraIndex;

    await fetch(apiUrl('/api/session/stop'), { method: 'POST' }).catch(() => undefined);

    const ok = await openCameraStream({ mode: 'dual', dualIndices });
    if (!ok) {
      const restored = await openCameraStream({ cameraIndex: fallbackIndex, mode: fallbackMode });
      if (restored) setIsAnalyzing(true);
      return false;
    }
    if (restartStream) setIsAnalyzing(true);
    return true;
  }

  async function selectDualCamera() {
    setConnectionError(null);
    await configureDualCamera(dualCamIndices, true);
  }

  async function swapDualCameras() {
    if (cameraMode !== 'dual' || isSwappingCameras) return;
    setIsSwappingCameras(true);
    const previous = dualCamIndices;
    const swapped = { front: previous.side, side: previous.front };
    const ok = await configureDualCamera(swapped, true);
    if (!ok) {
      setDualCamIndices(previous);
    }
    setIsSwappingCameras(false);
  }

  async function uploadVideo(file: File) {
    setConnectionError(null);
    setIsUploading(true);
    await fetch(apiUrl('/api/session/stop'), { method: 'POST' }).catch(() => undefined);
    stopCameraStream();
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

  const sideCameraIndex = availableCameras.length >= 2 ? availableCameras[1] : availableCameras[0] ?? 0;

  const sourceButtons = [
    { id: 'front', label: 'Kamera front', action: () => void selectCamera(availableCameras[0] ?? 0, 'front'), active: metrics.source === 'camera' && cameraMode === 'front' },
    { id: 'side', label: 'Kamera bok', action: () => void selectCamera(sideCameraIndex, 'side'), active: metrics.source === 'camera' && cameraMode === 'side' },
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
          {voiceSupported && (
            <button
              type="button"
              onClick={() => (voiceEnabled ? deactivateVoice() : void activateVoice())}
              disabled={voiceActivating}
              title={voiceEnabled ? 'Wyłącz sterowanie głosowe' : 'Włącz sterowanie głosowe'}
              className={clsx(
                'hidden rounded-xl border px-3 py-2 text-xs font-semibold transition-all sm:flex sm:items-center sm:gap-1.5',
                voiceEnabled
                  ? 'border-success/40 bg-success/10 text-success'
                  : 'border-white/10 bg-white/5 text-on-surface-variant hover:bg-white/10',
              )}
            >
              {voiceEnabled && isListening ? <Mic className="h-4 w-4" /> : <MicOff className="h-4 w-4" />}
              Głos
            </button>
          )}
          {cameraMode === 'dual' && (
            <button
              type="button"
              onClick={() => void swapDualCameras()}
              disabled={isSwappingCameras}
              title="Zamień kamerę frontową z boczną"
              className="hidden items-center gap-1.5 rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-xs font-semibold text-on-surface-variant transition-all hover:bg-white/10 disabled:opacity-50 md:flex"
            >
              <ArrowLeftRight className="h-4 w-4" />
              {isSwappingCameras ? 'Zamiana...' : 'Zamień kamery'}
            </button>
          )}
          <div className="hidden rounded-lg bg-surface-container p-1 md:flex">
            {sourceButtons.map((btn) => (
              <button
                key={btn.id}
                type="button"
                onClick={btn.action}
                disabled={btn.id === 'file' && isUploading}
                title={btn.id === 'dual' ? 'MacBook + iPhone (Continuity Camera)' : undefined}
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
            onClick={() => {
              if (canCancelTrial) void cancelTrial();
              else void startAnalysis();
            }}
            disabled={
              (!canStartTrial && !canCancelTrial && sessionStatus !== 'summary') ||
              (metrics.source === 'file' && !isVideoReady)
            }
            className={clsx(
              'rounded-xl px-5 py-2.5 text-sm font-bold transition-all',
              canCancelTrial ? 'bg-error/90 text-white hover:bg-error' : 'bg-primary-container text-on-primary-container hover:brightness-110',
              ((!canStartTrial && !canCancelTrial && sessionStatus !== 'summary') ||
                (metrics.source === 'file' && !isVideoReady)) &&
                'cursor-not-allowed opacity-50',
            )}
          >
            {canCancelTrial ? 'Anuluj próbę' : sessionStatus === 'summary' ? 'Nowa próba' : 'Rozpocznij'}
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
            <strong>Wskazówka Dual-Cam:</strong> iPhone musi być widoczny jako <strong>Continuity Camera</strong>{' '}
            (to samo Apple ID, Bluetooth + Wi‑Fi, iPhone odblokowany, „Zaufaj temu komputerowi”). Sam kabel USB
            ładuje telefon, ale nie zawsze włącza kamerę — sprawdź w FaceTime, czy widać iPhone na liście kamer.
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
                  key={feedKey}
                  src={`${apiUrl((metrics.cameraMode ?? cameraMode) === 'dual' ? '/video_feed_dual' : '/video_feed')}?t=${feedKey}`}
                  alt="Strumień analizy"
                  className="h-full w-full object-contain"
                  onError={() => {
                    if (isAnalyzingRef.current) {
                      window.setTimeout(() => setFeedKey((current) => current + 1), 800);
                    }
                  }}
                />
                {showSessionSetup && (
                  <SessionSetupOverlay
                    gotowosc={metrics.gotowoscPrzedOdbiciem}
                    postureWarnings={metrics.postureWarnings}
                    hasLegs={metrics.hasLegs}
                    hasPose={metrics.hasPose}
                    almostReady={setupAlmostReady}
                  />
                )}
                {showSessionTimer && (
                  <SessionTimerOverlay
                    phase={sessionStatus === 'prep' ? 'prep' : 'active'}
                    secondsRemaining={metrics.sessionSecondsRemaining ?? 0}
                  />
                )}
                {isSessionSummary && metrics.sessionSummary && (
                  <SessionSummaryOverlay summary={metrics.sessionSummary} />
                )}
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
                <p className="mt-4 text-on-surface-variant">Uruchamiam kamerę...</p>
                {selectedVideoName && metrics.source === 'file' && (
                  <p className="mt-2 text-sm text-primary-container">Plik: {selectedVideoName}</p>
                )}
              </div>
            )}

            {isAnalyzing && (
              <>
                <div className="absolute left-4 top-4 flex items-center gap-2 rounded-lg bg-red-600 px-3 py-1.5 shadow-lg">
                  <span className="h-2.5 w-2.5 animate-pulse rounded-full bg-white" />
                  <span className="text-xs font-bold uppercase tracking-widest text-white">Live</span>
                </div>

                {cameraCoachTip && (
                  <div
                    className={clsx(
                      'absolute right-3 top-1/2 z-20 max-w-[min(240px,38%)] -translate-y-1/2 rounded-2xl border px-4 py-3 shadow-lg backdrop-blur-md',
                      cameraCoachTip.positive
                        ? 'border-success/40 bg-success/20 text-green-100'
                        : 'border-primary-container/50 bg-primary-container/25 text-on-surface',
                    )}
                  >
                    <div className="flex items-start gap-2">
                      {cameraCoachTip.positive ? (
                        <CheckCircle2 className="mt-0.5 h-5 w-5 shrink-0 text-success" />
                      ) : (
                        <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-primary" />
                      )}
                      <span className="font-display text-sm font-bold leading-snug md:text-base">{cameraCoachTip.text}</span>
                    </div>
                  </div>
                )}

                <VoiceCommandBubble
                  heardText={heardText}
                  lastCommand={lastCommand}
                  isListening={isListening}
                  enabled={voiceEnabled}
                />

                {sessionStatus === 'idle' && (
                  <div className="absolute bottom-4 left-4 rounded-xl glass-panel px-4 py-3">
                    <p className="text-xs text-on-surface-variant">
                      Analiza na bieżąco — kliknij <strong>Rozpocznij</strong> na 10-sekundową próbę
                    </p>
                  </div>
                )}

                {!showSessionSetup && !showSessionTimer && !isSessionSummary && (
                  <div className="absolute bottom-4 right-4 flex flex-wrap items-center gap-4 rounded-xl glass-panel p-4">
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
                    {sessionStatus !== 'idle' && (
                      <>
                        <div className="h-10 w-px bg-white/10" />
                        <div>
                          <p className="text-xs font-semibold uppercase text-on-surface-variant">Odbicia</p>
                          <p className="font-display text-2xl font-bold text-primary-container">{metrics.totalContacts}</p>
                        </div>
                      </>
                    )}
                  </div>
                )}
              </>
            )}
          </div>

          <div className="flex flex-wrap gap-2 md:hidden">
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
            {cameraMode === 'dual' && (
              <button
                type="button"
                onClick={() => void swapDualCameras()}
                disabled={isSwappingCameras}
                className="shrink-0 rounded-lg border border-white/10 px-3 py-2 text-xs font-semibold text-on-surface-variant"
              >
                Zamień kamery
              </button>
            )}
          </div>
        </div>

        <aside className="flex flex-col gap-4 lg:col-span-3">
          <div className="glass-card rounded-2xl p-5">
            <ReadinessTiles
              gotowosc={metrics.gotowoscPrzedOdbiciem}
              postureWarnings={metrics.postureWarnings}
              hasLegs={metrics.hasLegs}
            />
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

        </aside>
      </main>
    </div>
  );
}
