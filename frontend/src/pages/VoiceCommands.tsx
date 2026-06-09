import { Link } from 'react-router-dom';
import { Mic, ArrowLeft } from 'lucide-react';
import { VOICE_COMMAND_LABELS } from '../context/VoiceCommandContext';

const commandRows = [
  { phrases: ['rozpocznij analizę', 'zacznij trening', 'włącz analizę'], id: 'start' as const },
  { phrases: ['zatrzymaj analizę', 'koniec analizy', 'zakończ trening'], id: 'stop' as const },
  { phrases: ['panel', 'strona główna', 'idź do panelu'], id: 'panel' as const },
  { phrases: ['analiza', 'przejdź do analizy'], id: 'analiza' as const },
  { phrases: ['historia', 'historia treningów'], id: 'historia' as const },
  { phrases: ['rozgrzewka', 'zacznij rozgrzewkę'], id: 'rozgrzewka' as const },
];

export default function VoiceCommands() {
  return (
    <div className="mx-auto max-w-3xl space-y-8">
      <div>
        <Link to="/dashboard" className="mb-4 inline-flex items-center gap-2 text-sm text-on-surface-variant hover:text-primary">
          <ArrowLeft className="h-4 w-4" />
          Wróć do panelu
        </Link>
        <div className="flex items-center gap-3">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-primary-container/20 text-primary">
            <Mic className="h-6 w-6" />
          </div>
          <div>
            <h1 className="font-display text-headline-lg text-on-surface">Komendy głosowe</h1>
            <p className="text-on-surface-variant">Włącz nasłuch w panelu bocznym i wypowiedz jedną z fraz.</p>
          </div>
        </div>
      </div>

      <div className="glass-card overflow-hidden">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-white/10 bg-surface-container-high/50">
              <th className="px-5 py-4 font-semibold text-on-surface-variant">Przykładowe frazy</th>
              <th className="px-5 py-4 font-semibold text-on-surface-variant">Akcja</th>
            </tr>
          </thead>
          <tbody>
            {commandRows.map((row) => (
              <tr key={row.id} className="border-b border-white/5">
                <td className="px-5 py-4 text-on-surface-variant">{row.phrases.join(' · ')}</td>
                <td className="px-5 py-4 font-medium text-primary">{VOICE_COMMAND_LABELS[row.id]}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="glass-card space-y-2 p-5 text-sm text-on-surface-variant">
        <p>
          <strong className="text-on-surface">Mikrofon:</strong> laptop — zezwól na dostęp w przeglądarce.
        </p>
        <p>
          <strong className="text-on-surface">Brave:</strong> używamy lokalnego Vosk na backendzie (port 8000).
        </p>
        <p>
          <strong className="text-on-surface">Live Analysis:</strong> komendy „rozpocznij” i „zatrzymaj” działają na stronie analizy.
        </p>
      </div>
    </div>
  );
}
