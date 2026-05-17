import { Calendar, ChevronRight } from 'lucide-react';

const mockHistory = [
  { id: 1, date: '14 Maj 2026', duration: '45 min', score: '85%', issue: 'Zbyt małe ugięcie kolan' },
  { id: 2, date: '12 Maj 2026', duration: '60 min', score: '78%', issue: 'Brak stabilności rąk' },
  { id: 3, date: '10 Maj 2026', duration: '30 min', score: '92%', issue: 'Drobne wahania postawy' },
];

export default function History() {
  return (
    <div className="max-w-6xl mx-auto flex flex-col gap-6">
      <header>
        <h2 className="text-3xl font-bold text-white mb-2">Historia Analiz</h2>
        <p className="text-on-surface-variant">Przeglądaj swoje wcześniejsze sesje treningowe i postępy.</p>
      </header>

      <div className="glass-card rounded-2xl overflow-hidden border-white/10">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="border-b border-white/10 bg-surface-variant/30">
              <th className="py-4 px-6 text-on-surface-variant font-medium text-sm">Data Treningu</th>
              <th className="py-4 px-6 text-on-surface-variant font-medium text-sm">Czas Trwania</th>
              <th className="py-4 px-6 text-on-surface-variant font-medium text-sm">Wynik</th>
              <th className="py-4 px-6 text-on-surface-variant font-medium text-sm">Główny Problem</th>
              <th className="py-4 px-6"></th>
            </tr>
          </thead>
          <tbody>
            {mockHistory.map((session) => (
              <tr key={session.id} className="border-b border-white/5 hover:bg-white/5 transition-colors group cursor-pointer">
                <td className="py-4 px-6">
                  <div className="flex items-center gap-3 text-white">
                    <div className="w-8 h-8 rounded-lg bg-surface-variant flex items-center justify-center">
                      <Calendar className="w-4 h-4 text-primary" />
                    </div>
                    {session.date}
                  </div>
                </td>
                <td className="py-4 px-6 text-on-surface-variant">{session.duration}</td>
                <td className="py-4 px-6">
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-500/10 text-green-400 border border-green-500/20">
                    {session.score}
                  </span>
                </td>
                <td className="py-4 px-6 text-on-surface-variant text-sm">{session.issue}</td>
                <td className="py-4 px-6 text-right">
                  <button className="p-2 rounded-lg text-on-surface-variant hover:text-white hover:bg-surface-variant transition-colors opacity-0 group-hover:opacity-100">
                    <ChevronRight className="w-5 h-5" />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
