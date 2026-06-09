import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { Activity, TrendingUp, Volleyball, AlertTriangle, ArrowRight, BarChart3 } from 'lucide-react';
import { PieChart, Pie, Cell, ResponsiveContainer } from 'recharts';
import { useAuth } from '../context/AuthContext';
import {
  fetchUserTrainings,
  formatDuration,
  formatTrainingDate,
  formatTrainingSource,
  getMainIssue,
  type TrainingWithStats,
} from '../lib/trainingData';
import { aggregateElementScores } from '../lib/elementScores';
import ElementBars from '../components/ui/ElementBars';

function calculateStats(trainings: TrainingWithStats[]) {
  const scores = trainings.map((t) => t.overall_score ?? 0);
  return {
    trainingCount: trainings.length,
    averageScore: scores.length ? Math.round(scores.reduce((a, b) => a + b, 0) / scores.length) : 0,
    bestScore: scores.length ? Math.max(...scores) : 0,
    totalContacts: trainings.reduce((sum, t) => sum + (t.stats?.total_contacts ?? 0), 0),
    totalWarnings: trainings.reduce((sum, t) => sum + (t.stats?.posture_warnings_count ?? 0), 0),
    lastTraining: trainings[0] ?? null,
  };
}

export default function Dashboard() {
  const { user, displayName } = useAuth();
  const [trainings, setTrainings] = useState<TrainingWithStats[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!user) return;
    let cancelled = false;
    setLoading(true);
    fetchUserTrainings(user.id)
      .then((result) => {
        if (!cancelled) setTrainings(result);
      })
      .catch(() => {
        if (!cancelled) setError('Nie udało się pobrać statystyk z bazy.');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [user]);

  const stats = useMemo(() => calculateStats(trainings), [trainings]);
  const elementScores = useMemo(() => aggregateElementScores(trainings), [trainings]);
  const pieData = [
    { name: 'Wynik', value: stats.averageScore, color: '#f97316' },
    { name: 'Do poprawy', value: 100 - stats.averageScore, color: '#352720' },
  ];

  return (
    <div className="mx-auto max-w-container space-y-8">
      <header className="flex flex-col justify-between gap-4 md:flex-row md:items-end">
        <div>
          <h1 className="font-display text-headline-lg text-on-surface">Dzień dobry, {displayName}</h1>
          <p className="mt-1 text-on-surface-variant">Twoje postępy i analiza techniki odbicia dolnego.</p>
        </div>
        <div className="flex items-center gap-2 rounded-full border border-white/10 bg-surface-container px-4 py-2">
          <span className="h-2 w-2 rounded-full bg-primary-container pulse-orange" />
          <span className="text-xs font-semibold uppercase tracking-wide text-on-surface-variant">System gotowy</span>
        </div>
      </header>

      {error && (
        <div className="rounded-xl border border-error/30 bg-error/10 px-4 py-3 text-error">{error}</div>
      )}

      {loading ? (
        <div className="glass-card p-10 text-center text-on-surface-variant">Ładowanie statystyk...</div>
      ) : trainings.length === 0 ? (
        <div className="glass-card p-10 text-center">
          <Activity className="mx-auto mb-4 h-10 w-10 text-primary" />
          <h2 className="font-display text-xl font-bold text-on-surface">Brak zapisanych treningów</h2>
          <p className="mt-2 text-on-surface-variant">Po pierwszej analizie pojawią się tutaj realne statystyki.</p>
          <Link to="/live" className="btn-primary mt-6 inline-flex items-center gap-2">
            Przejdź do analizy
            <ArrowRight className="h-5 w-5" />
          </Link>
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
            {[
              { label: 'Liczba treningów', value: stats.trainingCount, icon: Activity },
              { label: 'Średni wynik %', value: `${stats.averageScore}%`, icon: BarChart3 },
              { label: 'Najlepszy wynik %', value: `${stats.bestScore}%`, icon: TrendingUp },
              { label: 'Łączna liczba odbić', value: stats.totalContacts, icon: Volleyball },
            ].map((kpi) => (
              <div key={kpi.label} className="glass-card flex flex-col rounded-xl p-5">
                <span className="text-xs font-semibold uppercase tracking-widest text-on-surface-variant">{kpi.label}</span>
                <div className="mt-2 flex items-end justify-between">
                  <span className="font-display text-kpi-value text-on-surface">{kpi.value}</span>
                  <kpi.icon className="h-5 w-5 text-primary" />
                </div>
              </div>
            ))}
          </div>

          <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
            <div className="glass-card rounded-xl p-6 lg:col-span-2">
              <div className="mb-6 flex items-start justify-between">
                <h2 className="font-display text-headline-md text-on-surface">Poprawność elementów techniki</h2>
                <span className="rounded bg-surface-container-high px-2 py-1 text-xs text-on-surface-variant">Wszystkie sesje</span>
              </div>
              <ElementBars scores={elementScores} />
            </div>

            <div className="glass-card flex flex-col items-center rounded-xl p-6 text-center">
              <h2 className="font-display text-headline-md text-on-surface">Średnia skuteczność serii</h2>
              <div className="relative my-6 h-44 w-44">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie data={pieData} innerRadius={58} outerRadius={78} dataKey="value" stroke="none">
                      {pieData.map((entry) => (
                        <Cell key={entry.name} fill={entry.color} />
                      ))}
                    </Pie>
                  </PieChart>
                </ResponsiveContainer>
                <div className="absolute inset-0 flex items-center justify-center">
                  <span className="font-display text-4xl font-bold text-on-surface">{stats.averageScore}%</span>
                </div>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
            {stats.lastTraining && (
              <div className="glass-card flex gap-4 rounded-xl border-l-4 border-secondary p-5 lg:col-span-1">
                <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-lg bg-secondary/10">
                  <Volleyball className="h-7 w-7 text-secondary" />
                </div>
                <div>
                  <h3 className="font-display font-semibold text-on-surface">Ostatni trening</h3>
                  <p className="text-sm text-on-surface-variant">{formatTrainingDate(stats.lastTraining.start_time)}</p>
                  <p className="mt-1 text-sm text-on-surface-variant">
                    {formatTrainingSource(stats.lastTraining.source)} · {formatDuration(stats.lastTraining.start_time, stats.lastTraining.end_time)}
                  </p>
                  <p className="mt-2 text-sm">
                    Wynik: <strong className="text-primary">{stats.lastTraining.overall_score ?? 0}%</strong> · Odbicia:{' '}
                    {stats.lastTraining.stats?.total_contacts ?? 0}
                  </p>
                </div>
              </div>
            )}

            <div className="glass-card flex gap-4 rounded-xl border-l-4 border-error p-5 lg:col-span-1">
              <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-error/10">
                <AlertTriangle className="h-6 w-6 text-error" />
              </div>
              <div>
                <h3 className="font-display font-semibold text-on-surface">Do poprawy</h3>
                <p className="mt-1 font-medium text-on-surface">{getMainIssue(stats.totalWarnings)}</p>
                <p className="mt-1 text-sm text-on-surface-variant">
                  {stats.totalWarnings > 0
                    ? 'Najczęściej: ugięcie kolan — skup się na amortyzacji nóg.'
                    : 'Kontynuuj trening — brak powtarzających się błędów.'}
                </p>
              </div>
            </div>

            <Link
              to="/live"
              className="btn-primary flex min-h-[120px] flex-col items-center justify-center gap-2 rounded-xl lg:col-span-1"
            >
              <ArrowRight className="h-8 w-8" />
              <span className="font-display text-lg font-bold">Przejdź do analizy</span>
            </Link>
          </div>
        </>
      )}
    </div>
  );
}
