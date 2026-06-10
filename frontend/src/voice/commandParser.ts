export type VoiceCommandId = 'start' | 'stop' | 'panel' | 'rozgrzewka' | 'analiza' | 'historia';

export const VOICE_COMMAND_LABELS: Record<VoiceCommandId, string> = {
  start: 'Rozpocznij',
  stop: 'Zatrzymaj',
  panel: 'Panel',
  rozgrzewka: 'Rozgrzewka',
  analiza: 'Analiza',
  historia: 'Historia',
};

const PHRASE_RULES: { id: VoiceCommandId; phrases: string[] }[] = [
  {
    id: 'rozgrzewka',
    phrases: [
      'idź do rozgrzewki',
      'otwórz rozgrzewkę',
      'przejdź do rozgrzewki',
      'pokaż rozgrzewkę',
      'zacznij rozgrzewkę',
    ],
  },
  {
    id: 'historia',
    phrases: [
      'idź do historii',
      'otwórz historię',
      'przejdź do historii',
      'pokaż historię',
      'historia treningów',
    ],
  },
  {
    id: 'analiza',
    phrases: [
      'idź do analizy',
      'otwórz analizę',
      'przejdź do analizy',
      'strona analizy',
      'analiza treningu',
    ],
  },
  {
    id: 'panel',
    phrases: [
      'idź do panelu',
      'otwórz panel',
      'przejdź do panelu',
      'panel główny',
      'strona główna',
    ],
  },
  {
    id: 'start',
    phrases: [
      'rozpocznij analizę',
      'rozpocznij analize',
      'włącz analizę',
      'wlacz analize',
      'start analizy',
      'zacznij analizę',
      'zacznij analize',
      'rozpocznij trening',
      'zacznij trening',
      'rozpocznij',
      'zacznij',
      'start',
    ],
  },
  {
    id: 'stop',
    phrases: [
      'zatrzymaj analizę',
      'zatrzymaj analize',
      'wyłącz analizę',
      'wylacz analize',
      'stop analizy',
      'koniec analizy',
      'zatrzymaj trening',
      'zakończ trening',
      'zatrzymaj',
      'koniec',
      'stop',
    ],
  },
];

const KEYWORD_RULES: { id: VoiceCommandId; patterns: RegExp[] }[] = [
  {
    id: 'rozgrzewka',
    patterns: [/\brozgrzewka\b/, /\brozgrzewke\b/, /\brozgrzewki\b/],
  },
  {
    id: 'historia',
    patterns: [/\bhistoria\b/, /\bhistorie\b/, /\bhistorii\b/],
  },
  {
    id: 'analiza',
    patterns: [/\banaliza\b/, /\banalize\b/, /\banalizy\b/],
  },
  {
    id: 'panel',
    patterns: [/\bpanel\b/, /\bpanelu\b/, /\bglowna\b/, /\bgłówna\b/],
  },
  {
    id: 'start',
    patterns: [/\brozpocznij\b/, /\bzacznij\b/, /\bwlacz\b/, /\bwłącz\b/, /\bstart\b/],
  },
  {
    id: 'stop',
    patterns: [/\bzatrzymaj\b/, /\bzatrzymac\b/, /\bzatrzymać\b/, /\bwylacz\b/, /\bwyłącz\b/, /\bstop\b/, /\bkoniec\b/],
  },
];

const FUZZY_WORDS: { id: VoiceCommandId; variants: string[]; maxDistance: number }[] = [
  { id: 'panel', variants: ['panel', 'panelu'], maxDistance: 1 },
  { id: 'rozgrzewka', variants: ['rozgrzewka', 'rozgrzewke', 'rozgrzewki'], maxDistance: 2 },
  { id: 'analiza', variants: ['analiza', 'analize', 'analizy'], maxDistance: 2 },
  { id: 'historia', variants: ['historia', 'historie', 'historii'], maxDistance: 2 },
  {
    id: 'start',
    variants: ['start', 'rozpocznij', 'zacznij', 'wlacz', 'wlaczyc'],
    maxDistance: 2,
  },
  {
    id: 'stop',
    variants: ['stop', 'zatrzymaj', 'koniec', 'wylacz', 'wylaczyc'],
    maxDistance: 2,
  },
];

export function normalizeTranscript(text: string): string {
  return text
    .toLowerCase()
    .normalize('NFD')
    .replace(/\p{M}/gu, '')
    .replace(/[^\p{L}\p{N}\s]/gu, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

function levenshtein(a: string, b: string): number {
  if (a === b) return 0;
  if (!a.length) return b.length;
  if (!b.length) return a.length;

  const matrix = Array.from({ length: a.length + 1 }, () => new Array<number>(b.length + 1).fill(0));

  for (let i = 0; i <= a.length; i += 1) matrix[i][0] = i;
  for (let j = 0; j <= b.length; j += 1) matrix[0][j] = j;

  for (let i = 1; i <= a.length; i += 1) {
    for (let j = 1; j <= b.length; j += 1) {
      const cost = a[i - 1] === b[j - 1] ? 0 : 1;
      matrix[i][j] = Math.min(
        matrix[i - 1][j] + 1,
        matrix[i][j - 1] + 1,
        matrix[i - 1][j - 1] + cost,
      );
    }
  }

  return matrix[a.length][b.length];
}

function matchByPhrases(normalized: string): VoiceCommandId | null {
  const sorted = [...PHRASE_RULES].flatMap((rule) =>
    rule.phrases.map((phrase) => ({ id: rule.id, phrase })),
  );
  sorted.sort((a, b) => b.phrase.length - a.phrase.length);

  for (const { id, phrase } of sorted) {
    if (normalized.includes(normalizeTranscript(phrase))) {
      return id;
    }
  }
  return null;
}

function matchByKeywords(normalized: string): VoiceCommandId | null {
  for (const rule of KEYWORD_RULES) {
    if (rule.patterns.some((pattern) => pattern.test(normalized))) {
      return rule.id;
    }
  }
  return null;
}

function matchByFuzzy(normalized: string): VoiceCommandId | null {
  const tokens = normalized.split(' ').filter(Boolean);

  for (const token of tokens) {
    for (const { id, variants, maxDistance } of FUZZY_WORDS) {
      for (const variant of variants) {
        if (levenshtein(token, variant) <= maxDistance) {
          return id;
        }
      }
    }
  }

  return null;
}

export function matchVoiceCommand(transcript: string): VoiceCommandId | null {
  const normalized = normalizeTranscript(transcript);
  if (!normalized) return null;

  return matchByPhrases(normalized) ?? matchByKeywords(normalized) ?? matchByFuzzy(normalized);
}
