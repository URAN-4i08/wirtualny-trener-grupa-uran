export type VoiceCommandId = 'start' | 'stop' | 'panel' | 'analiza';

export const VOICE_COMMAND_LABELS: Record<VoiceCommandId, string> = {
  start: 'Rozpocznij',
  stop: 'Zatrzymaj',
  panel: 'Panel',
  analiza: 'Analiza',
};

/** Dłuższe frazy pierwsze — ważna kolejność dopasowania. */
const PHRASE_RULES: { id: VoiceCommandId; phrases: string[] }[] = [
  {
    id: 'analiza',
    phrases: [
      'idz do analizy',
      'otworz analize',
      'przejdz do analizy',
      'analiza live',
      'live analysis',
      'strona analizy',
    ],
  },
  {
    id: 'panel',
    phrases: [
      'idz do panelu',
      'otworz panel',
      'przejdz do panelu',
      'panel glowny',
      'strona glowna',
    ],
  },
  {
    id: 'start',
    phrases: [
      'rozpocznij analize',
      'wlacz analize',
      'start analizy',
      'start analysis',
      'begin analysis',
      'zacznij analize',
    ],
  },
  {
    id: 'stop',
    phrases: [
      'zatrzymaj analize',
      'wylacz analize',
      'stop analizy',
      'stop analysis',
      'koniec analizy',
    ],
  },
];

/** Pojedyncze słowa PL + EN. */
const KEYWORD_RULES: { id: VoiceCommandId; patterns: RegExp[] }[] = [
  {
    id: 'analiza',
    patterns: [/\banaliza\b/, /\banalize\b/, /\blive\b.*\banaliz/],
  },
  {
    id: 'panel',
    patterns: [/\bpanel\b/, /\bpanelu\b/, /\bpanelu\b/],
  },
  {
    id: 'start',
    patterns: [/\brozpocznij\b/, /\bzacznij\b/, /\bwlacz\b/, /\bstart\b/, /\bbegin\b/],
  },
  {
    id: 'stop',
    patterns: [/\bzatrzymaj\b/, /\bzatrzymac\b/, /\bwylacz\b/, /\bstop\b/, /\bend\b/, /\bkoniec\b/],
  },
];

const FUZZY_WORDS: { id: VoiceCommandId; variants: string[]; maxDistance: number }[] = [
  { id: 'panel', variants: ['panel', 'panelu', 'panels'], maxDistance: 1 },
  { id: 'analiza', variants: ['analiza', 'analize', 'analizy'], maxDistance: 1 },
  { id: 'start', variants: ['start', 'starts'], maxDistance: 1 },
  { id: 'stop', variants: ['stop', 'stops'], maxDistance: 1 },
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
