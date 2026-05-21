import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from 'react';
import { useNavigate } from 'react-router-dom';
import { apiUrl, wsUrl } from '../config/api';
import { matchVoiceCommand, VOICE_COMMAND_LABELS, type VoiceCommandId } from '../voice/commandParser';
import { requestMicrophonePermission, startMicrophoneCapture } from '../voice/audioCapture';
import { shouldPreferBackendVoice } from '../voice/browser';
import { createSpeechRecognition, isSpeechRecognitionSupported } from '../voice/speechRecognition';

type LiveVoiceHandlers = {
  startAnalysis: () => void;
  stopAnalysis: () => void;
};

type VoiceEngine = 'vosk' | 'webspeech' | 'off';

type VoiceCommandContextValue = {
  isSupported: boolean;
  isListening: boolean;
  enabled: boolean;
  isActivating: boolean;
  activateVoice: () => Promise<void>;
  deactivateVoice: () => void;
  engine: VoiceEngine;
  lastCommand: VoiceCommandId | null;
  lastTranscript: string | null;
  heardText: string | null;
  error: string | null;
  isPreparing: boolean;
  registerLiveHandlers: (handlers: LiveVoiceHandlers | null) => void;
};

const VoiceCommandContext = createContext<VoiceCommandContextValue | null>(null);

const COMMAND_COOLDOWN_MS = 2000;

export function VoiceCommandProvider({ children }: { children: ReactNode }) {
  const navigate = useNavigate();
  const liveHandlersRef = useRef<LiveVoiceHandlers | null>(null);
  const recognitionRef = useRef<ReturnType<typeof createSpeechRecognition> | null>(null);
  const voiceSocketRef = useRef<WebSocket | null>(null);
  const micCaptureRef = useRef<{ stop: () => void } | null>(null);
  const lastFiredAtRef = useRef<Record<string, number>>({});
  const enabledRef = useRef(false);
  const engineRef = useRef<VoiceEngine>('off');

  const [enabled, setEnabled] = useState(false);
  const [isActivating, setIsActivating] = useState(false);
  const [engine, setEngine] = useState<VoiceEngine>('off');
  const [isListening, setIsListening] = useState(false);
  const [isPreparing, setIsPreparing] = useState(false);
  const [lastCommand, setLastCommand] = useState<VoiceCommandId | null>(null);
  const [lastTranscript, setLastTranscript] = useState<string | null>(null);
  const [heardText, setHeardText] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [backendVoiceReady, setBackendVoiceReady] = useState(false);
  const [voiceBootstrapDone, setVoiceBootstrapDone] = useState(false);

  useEffect(() => {
    enabledRef.current = enabled;
  }, [enabled]);

  const hasMicrophoneApi =
    typeof navigator !== 'undefined' && Boolean(navigator.mediaDevices?.getUserMedia);

  const isSupported = hasMicrophoneApi && (backendVoiceReady || isSpeechRecognitionSupported());

  const registerLiveHandlers = useCallback((handlers: LiveVoiceHandlers | null) => {
    liveHandlersRef.current = handlers;
  }, []);

  const processTranscript = useCallback((transcript: string) => {
    const trimmed = transcript.trim();
    if (!trimmed) return;

    setHeardText(trimmed);
    const commandId = matchVoiceCommand(trimmed);
    if (!commandId) return;

    const now = Date.now();
    if (now - (lastFiredAtRef.current[commandId] ?? 0) < COMMAND_COOLDOWN_MS) {
      return;
    }
    lastFiredAtRef.current[commandId] = now;

    setLastCommand(commandId);
    setLastTranscript(trimmed);
    setError(null);

    switch (commandId) {
      case 'start':
        liveHandlersRef.current?.startAnalysis();
        break;
      case 'stop':
        liveHandlersRef.current?.stopAnalysis();
        break;
      case 'panel':
        navigate('/dashboard');
        break;
      case 'analiza':
        navigate('/live');
        break;
      default:
        break;
    }
  }, [navigate]);

  const stopVoskSession = useCallback(() => {
    micCaptureRef.current?.stop();
    micCaptureRef.current = null;
    voiceSocketRef.current?.close();
    voiceSocketRef.current = null;
    setIsListening(false);
  }, []);

  const stopWebSpeech = useCallback(() => {
    recognitionRef.current?.abort();
    recognitionRef.current = null;
    setIsListening(false);
  }, []);

  const startVoskSession = useCallback(async () => {
    stopVoskSession();
    engineRef.current = 'vosk';
    setEngine('vosk');
    setError(null);

    const socket = new WebSocket(wsUrl('/ws/voice'));
    voiceSocketRef.current = socket;

    socket.onopen = async () => {
      try {
        const capture = await startMicrophoneCapture((chunk) => {
          if (socket.readyState === WebSocket.OPEN) {
            socket.send(chunk);
          }
        });
        micCaptureRef.current = capture;
        setIsListening(true);
        setError(null);
      } catch {
        setError('Nie udało się użyć mikrofonu. Sprawdź uprawnienia w przeglądarce.');
        setEnabled(false);
        setIsListening(false);
      }
    };

    socket.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        if (payload.type === 'error') {
          setEnabled(false);
          setIsListening(false);
          setError(payload.message || 'Blad rozpoznawania mowy. Zrestartuj backend i sprobuj ponownie.');
          stopVoskSession();
          return;
        }
        if (payload.type === 'partial' || payload.type === 'final') {
          processTranscript(payload.text || '');
        }
      } catch {
        setError('Nie udało się odczytać wyniku rozpoznawania mowy.');
      }
    };

    socket.onerror = () => {
      setError('Brak połączenia z serwerem głosu. Uruchom backend na porcie 8000.');
      setIsListening(false);
    };

    socket.onclose = () => {
      micCaptureRef.current?.stop();
      micCaptureRef.current = null;
      setIsListening(false);
    };
  }, [processTranscript, stopVoskSession]);

  const startWebSpeechSession = useCallback(() => {
    stopWebSpeech();
    const recognition = createSpeechRecognition();
    if (!recognition) {
      setError('Przeglądarka nie obsługuje rozpoznawania mowy.');
      return;
    }

    engineRef.current = 'webspeech';
    setEngine('webspeech');
    recognitionRef.current = recognition;

    recognition.onresult = (event: SpeechRecognitionEvent) => {
      const lastResult = event.results[event.results.length - 1];
      processTranscript(lastResult?.[0]?.transcript || '');
    };

    recognition.onerror = (event: SpeechRecognitionErrorEvent) => {
      if (event.error === 'no-speech' || event.error === 'aborted') return;
      if (event.error === 'network') {
        setError('Przeglądarka zablokowała usługę mowy. Przełączam na lokalny Vosk...');
        void startVoskSession();
        return;
      }
      setError(`Błąd mikrofonu: ${event.error}`);
      setIsListening(false);
    };

    recognition.onend = () => {
      setIsListening(false);
      if (!enabledRef.current || engineRef.current !== 'webspeech') return;
      window.setTimeout(() => {
        try {
          recognition.start();
          setIsListening(true);
        } catch {
          setError('Nie udało się wznowić nasłuchu głosowego.');
        }
      }, 400);
    };

    try {
      recognition.start();
      setIsListening(true);
      setError(null);
    } catch {
      setError('Brak dostępu do mikrofonu.');
      setEnabled(false);
      setIsListening(false);
    }
  }, [processTranscript, startVoskSession, stopWebSpeech]);

  const deactivateVoice = useCallback(() => {
    setEnabled(false);
    setIsActivating(false);
    setError(null);
  }, []);

  const activateVoice = useCallback(async () => {
    if (!hasMicrophoneApi) {
      setError('Ta przeglądarka nie obsługuje mikrofonu.');
      return;
    }

    setIsActivating(true);
    setError(null);

    try {
      await requestMicrophonePermission();
    } catch {
      setError('Brak dostępu do mikrofonu. Kliknij „Zezwól” w oknie przeglądarki i spróbuj ponownie.');
      setIsActivating(false);
      return;
    }

    if (!voiceBootstrapDone) {
      setError('Ładowanie silnika głosu — poczekaj chwilę i kliknij ponownie.');
      setIsActivating(false);
      return;
    }

    if (!backendVoiceReady && !isSpeechRecognitionSupported()) {
      setError('Uruchom backend na porcie 8000 (server.py).');
      setIsActivating(false);
      return;
    }

    setEnabled(true);
    setIsActivating(false);
  }, [backendVoiceReady, hasMicrophoneApi, voiceBootstrapDone]);

  useEffect(() => {
    let cancelled = false;

    async function bootstrapVoice() {
      try {
        const statusResponse = await fetch(apiUrl('/api/voice/status'));
        const status = await statusResponse.json();
        if (cancelled) return;

        if (!status.ready) {
          setIsPreparing(true);
          const prepareResponse = await fetch(apiUrl('/api/voice/prepare'), { method: 'POST' });
          const prepareResult = await prepareResponse.json();
          if (cancelled) return;
          setIsPreparing(false);

          if (!prepareResponse.ok || !prepareResult.ready) {
            setBackendVoiceReady(false);
            return;
          }
        }

        setBackendVoiceReady(true);
      } catch {
        if (!cancelled) setBackendVoiceReady(false);
      } finally {
        if (!cancelled) setVoiceBootstrapDone(true);
      }
    }

    bootstrapVoice();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!enabled || !voiceBootstrapDone) {
      stopVoskSession();
      stopWebSpeech();
      engineRef.current = 'off';
      setEngine('off');
      return;
    }

    let cancelled = false;

    async function startListening() {
      const preferBackend = (await shouldPreferBackendVoice()) || backendVoiceReady;

      if (preferBackend && backendVoiceReady) {
        if (!cancelled) await startVoskSession();
        return;
      }

      if (isSpeechRecognitionSupported() && !(await shouldPreferBackendVoice())) {
        if (!cancelled) startWebSpeechSession();
        return;
      }

      if (backendVoiceReady) {
        if (!cancelled) await startVoskSession();
        return;
      }

      setError('Brak silnika rozpoznawania mowy. Uruchom backend i pobierz model Vosk.');
      setEnabled(false);
    }

    startListening();

    return () => {
      cancelled = true;
      stopVoskSession();
      stopWebSpeech();
    };
  }, [
    backendVoiceReady,
    enabled,
    startVoskSession,
    startWebSpeechSession,
    stopVoskSession,
    stopWebSpeech,
    voiceBootstrapDone,
  ]);

  const value = useMemo(
    () => ({
      isSupported,
      isListening,
      enabled,
      isActivating,
      activateVoice,
      deactivateVoice,
      engine,
      lastCommand,
      lastTranscript,
      heardText,
      error,
      isPreparing,
      registerLiveHandlers,
    }),
    [
      activateVoice,
      deactivateVoice,
      enabled,
      engine,
      error,
      heardText,
      isActivating,
      isListening,
      isPreparing,
      isSupported,
      lastCommand,
      lastTranscript,
      registerLiveHandlers,
    ],
  );

  return <VoiceCommandContext.Provider value={value}>{children}</VoiceCommandContext.Provider>;
}

export function useVoiceCommands() {
  const context = useContext(VoiceCommandContext);
  if (!context) {
    throw new Error('useVoiceCommands must be used within VoiceCommandProvider');
  }
  return context;
}

export { VOICE_COMMAND_LABELS };
