export type BrowserSpeechRecognition = {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  maxAlternatives: number;
  onresult: ((event: SpeechRecognitionEvent) => void) | null;
  onerror: ((event: SpeechRecognitionErrorEvent) => void) | null;
  onend: (() => void) | null;
  start: () => void;
  stop: () => void;
  abort: () => void;
};

type SpeechRecognitionConstructor = new () => BrowserSpeechRecognition;

declare global {
  interface Window {
    SpeechRecognition?: SpeechRecognitionConstructor;
    webkitSpeechRecognition?: SpeechRecognitionConstructor;
  }
}

export function createSpeechRecognition(): BrowserSpeechRecognition | null {
  const SpeechRecognitionCtor = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognitionCtor) return null;

  const recognition = new SpeechRecognitionCtor();
  recognition.lang = 'pl-PL';
  recognition.continuous = true;
  recognition.interimResults = false;
  recognition.maxAlternatives = 1;
  return recognition;
}

export function isSpeechRecognitionSupported(): boolean {
  return createSpeechRecognition() !== null;
}
