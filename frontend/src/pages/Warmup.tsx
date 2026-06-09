import { useEffect, useMemo, useState } from 'react';
import { ArrowRight, CheckCircle2, Flame, Pause, Play, RotateCcw, Timer, Volleyball } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { clsx } from 'clsx';
import ExerciseIllustration from '../components/warmup/ExerciseIllustration';

type WarmupMode = 'short' | 'standard' | 'strong';

type WarmupExercise = {
  name: string;
  duration: number;
  instruction: string;
};

type WarmupPlan = {
  id: WarmupMode;
  name: string;
  series: number;
  description: string;
  exercises: WarmupExercise[];
};

const warmupPlans: WarmupPlan[] = [
  {
    id: 'short',
    name: 'Krótka',
    series: 1,
    description: 'Szybkie wejście w ruch przed lekką analizą.',
    exercises: [
      {
        name: 'Krążenia ramion',
        duration: 15,
        instruction: 'Wykonuj płynne krążenia ramion w przód i w tył.',
      },
      {
        name: 'Nadgarstki i dłonie',
        duration: 15,
        instruction: 'Rozgrzej nadgarstki, palce i przedramiona.',
      },
      {
        name: 'Lekkie odbicia bez liczenia',
        duration: 20,
        instruction: 'Ustaw ręce jak do przyjęcia i wykonuj spokojne odbicia.',
      },
    ],
  },
  {
    id: 'standard',
    name: 'Standardowa',
    series: 2,
    description: 'Najlepszy wybór przed normalnym treningiem techniki.',
    exercises: [
      {
        name: 'Krążenia ramion',
        duration: 20,
        instruction: 'Rozluźnij barki i utrzymaj równy oddech.',
      },
      {
        name: 'Przysiady techniczne',
        duration: 25,
        instruction: 'Zejdź nisko, pilnuj kolan i stabilnych stóp.',
      },
      {
        name: 'Wykroki naprzemienne',
        duration: 25,
        instruction: 'Pracuj spokojnie, bez szarpania ruchu.',
      },
      {
        name: 'Lekkie odbicia bez liczenia',
        duration: 30,
        instruction: 'Przygotuj ręce i czucie piłki przed serią.',
      },
    ],
  },
  {
    id: 'strong',
    name: 'Mocna',
    series: 3,
    description: 'Pełniejsze przygotowanie przed intensywną serią.',
    exercises: [
      {
        name: 'Krążenia ramion',
        duration: 25,
        instruction: 'Zacznij od małych ruchów i stopniowo zwiększ zakres.',
      },
      {
        name: 'Przysiady techniczne',
        duration: 30,
        instruction: 'Pilnuj niskiej pozycji i aktywnych nóg.',
      },
      {
        name: 'Wykroki naprzemienne',
        duration: 30,
        instruction: 'Utrzymaj stabilny tułów i spokojny rytm.',
      },
      {
        name: 'Plank',
        duration: 25,
        instruction: 'Napnij brzuch i utrzymaj prostą linię ciała.',
      },
      {
        name: 'Lekkie odbicia bez liczenia',
        duration: 35,
        instruction: 'Wejdź w rytm odbić przed właściwą analizą.',
      },
    ],
  },
];

function formatTime(totalSeconds: number) {
  const minutes = Math.floor(totalSeconds / 60).toString().padStart(2, '0');
  const seconds = (totalSeconds % 60).toString().padStart(2, '0');
  return `${minutes}:${seconds}`;
}

export default function Warmup() {
  const navigate = useNavigate();
  const [selectedMode, setSelectedMode] = useState<WarmupMode>('standard');
  const [exerciseIndex, setExerciseIndex] = useState(0);
  const [seriesIndex, setSeriesIndex] = useState(1);
  const [isRunning, setIsRunning] = useState(false);
  const [isFinished, setIsFinished] = useState(false);

  const plan = useMemo(
    () => warmupPlans.find((item) => item.id === selectedMode) ?? warmupPlans[1],
    [selectedMode],
  );
  const currentExercise = plan.exercises[exerciseIndex];
  const [timeLeft, setTimeLeft] = useState(currentExercise.duration);
  const totalSteps = plan.exercises.length * plan.series;
  const completedSteps = (seriesIndex - 1) * plan.exercises.length + exerciseIndex;
  const progress = isFinished ? 100 : Math.round((completedSteps / totalSteps) * 100);

  useEffect(() => {
    setExerciseIndex(0);
    setSeriesIndex(1);
    setIsRunning(false);
    setIsFinished(false);
    setTimeLeft(plan.exercises[0].duration);
  }, [plan]);

  useEffect(() => {
    setTimeLeft(currentExercise.duration);
  }, [currentExercise.duration]);

  useEffect(() => {
    if (!isRunning || isFinished) return;

    const timerId = window.setInterval(() => {
      setTimeLeft((current) => {
        if (current > 1) return current - 1;

        window.clearInterval(timerId);
        goToNextStep();
        return 0;
      });
    }, 1000);

    return () => window.clearInterval(timerId);
  }, [isFinished, isRunning, exerciseIndex, seriesIndex, plan]);

  function goToNextStep() {
    setExerciseIndex((current) => {
      if (current < plan.exercises.length - 1) {
        return current + 1;
      }

      if (seriesIndex < plan.series) {
        setSeriesIndex((series) => series + 1);
        return 0;
      }

      setIsRunning(false);
      setIsFinished(true);
      return current;
    });
  }

  function resetWarmup() {
    setExerciseIndex(0);
    setSeriesIndex(1);
    setIsRunning(false);
    setIsFinished(false);
    setTimeLeft(plan.exercises[0].duration);
  }

  return (
    <div className="mx-auto flex max-w-container flex-col gap-6 pb-10">
      <header className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <h1 className="font-display text-headline-lg text-on-surface">Rozgrzewka</h1>
          <p className="mt-1 text-on-surface-variant">
            Wybierz wariant i przejdź przez krótkie przygotowanie przed analizą z kamery.
          </p>
        </div>
        <button type="button" onClick={() => navigate('/live')} className="btn-primary flex w-fit items-center gap-2">
          Przejdź do analizy
          <ArrowRight className="h-5 w-5" />
        </button>
      </header>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        {warmupPlans.map((item) => (
          <button
            key={item.id}
            type="button"
            onClick={() => setSelectedMode(item.id)}
            className={clsx(
              'rounded-2xl border p-5 text-left transition',
              selectedMode === item.id
                ? 'border-primary/40 bg-primary/10 text-white'
                : 'border-white/10 bg-surface-variant/30 text-on-surface-variant hover:bg-surface-variant/60',
            )}
          >
            <div className="mb-3 flex items-center justify-between gap-3">
              <span className="text-lg font-bold text-white">{item.name}</span>
              <span className="rounded-full border border-white/10 px-3 py-1 text-xs">{item.series} serie</span>
            </div>
            <p className="text-sm leading-relaxed">{item.description}</p>
          </button>
        ))}
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-[1fr_360px]">
        <section className="glass-card rounded-2xl p-6">
          <div className="mb-6 grid gap-6 md:grid-cols-[200px_1fr] md:items-center">
            <div className="mx-auto flex h-40 w-full max-w-[200px] items-center justify-center rounded-2xl border border-white/10 bg-surface-container-high/50 p-4">
              <ExerciseIllustration name={currentExercise.name} />
            </div>
            <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <p className="text-sm text-on-surface-variant">Teraz wykonuj</p>
                <h3 className="mt-1 font-display text-3xl font-bold text-on-surface">{currentExercise.name}</h3>
              </div>
              <div className="flex items-center gap-3 rounded-2xl bg-black/25 px-5 py-4">
                <Timer className="h-7 w-7 text-primary" />
                <span className="font-display text-5xl font-bold tabular-nums text-on-surface">{formatTime(timeLeft)}</span>
              </div>
            </div>
          </div>

          <div className="rounded-2xl border border-white/10 bg-surface-variant/30 p-5">
            <p className="text-xl font-semibold text-white">{currentExercise.instruction}</p>
            <p className="mt-3 text-sm text-on-surface-variant">
              Seria {seriesIndex} z {plan.series}. Krok {exerciseIndex + 1} z {plan.exercises.length}.
            </p>
          </div>

          <div className="mt-6 h-3 overflow-hidden rounded-full bg-surface-variant">
            <div className="h-full bg-primary transition-all duration-300" style={{ width: `${progress}%` }} />
          </div>

          <div className="mt-6 flex flex-wrap gap-3">
            <button
              type="button"
              onClick={() => setIsRunning((current) => !current)}
              disabled={isFinished}
              className={clsx(
                'flex items-center gap-2 rounded-full px-6 py-3 font-bold transition',
                isFinished
                  ? 'cursor-not-allowed bg-surface-variant text-on-surface-variant'
                  : 'bg-primary text-surface hover:bg-primary-container',
              )}
            >
              {isRunning ? <Pause className="h-5 w-5" /> : <Play className="h-5 w-5" />}
              {isRunning ? 'Pauza' : 'Start'}
            </button>
            <button
              type="button"
              onClick={goToNextStep}
              disabled={isFinished}
              className="flex items-center gap-2 rounded-full border border-white/10 px-6 py-3 font-bold text-white transition hover:bg-white/5 disabled:cursor-not-allowed disabled:opacity-50"
            >
              Następne
              <ArrowRight className="h-5 w-5" />
            </button>
            <button
              type="button"
              onClick={resetWarmup}
              className="flex items-center gap-2 rounded-full border border-white/10 px-6 py-3 font-bold text-white transition hover:bg-white/5"
            >
              <RotateCcw className="h-5 w-5" />
              Reset
            </button>
          </div>

          {isFinished && (
            <div className="mt-6 rounded-2xl border border-green-500/30 bg-green-500/10 p-5">
              <div className="flex items-start gap-3">
                <CheckCircle2 className="mt-0.5 h-6 w-6 text-green-400" />
                <div>
                  <p className="font-bold text-green-300">Rozgrzewka zakończona</p>
                  <p className="mt-1 text-sm text-on-surface-variant">
                    Możesz przejść do analizy i rozpocząć właściwą serię.
                  </p>
                </div>
              </div>
            </div>
          )}
        </section>

        <aside className="glass-card rounded-2xl p-6 h-fit">
          <div className="mb-5 flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
              <Flame className="h-5 w-5 text-primary" />
            </div>
            <div>
              <h3 className="font-bold text-white">Plan ćwiczeń</h3>
              <p className="text-xs text-on-surface-variant">{plan.name}, {plan.series} serie</p>
            </div>
          </div>

          <div className="flex flex-col gap-3">
            {plan.exercises.map((exercise, index) => (
              <div
                key={exercise.name}
                className={clsx(
                  'rounded-xl border p-4',
                  index === exerciseIndex && !isFinished
                    ? 'border-primary/40 bg-primary/10'
                    : 'border-white/10 bg-surface-variant/20',
                )}
              >
                <div className="flex items-center justify-between gap-3">
                  <p className="font-semibold text-white">{exercise.name}</p>
                  <span className="text-xs text-on-surface-variant">{exercise.duration} s</span>
                </div>
              </div>
            ))}
          </div>

          <div className="mt-6 rounded-xl border border-white/10 bg-surface-variant/20 p-4">
            <div className="mb-2 flex items-center gap-2 text-primary">
              <Volleyball className="h-4 w-4" />
              <span className="text-sm font-bold">Po rozgrzewce</span>
            </div>
            <p className="text-sm text-on-surface-variant">
              Analiza pliku wideo nie wymaga rozgrzewki. Ten panel przygotowuje tylko trening z kamerą.
            </p>
          </div>
        </aside>
      </div>
    </div>
  );
}
