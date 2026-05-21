import { NavLink } from 'react-router-dom';
import { LayoutDashboard, Video, History as HistoryIcon, Dumbbell, Mic, MicOff, Loader2 } from 'lucide-react';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';
import { useVoiceCommands, VOICE_COMMAND_LABELS } from '../context/VoiceCommandContext';

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

const navItems = [
  { path: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { path: '/live', label: 'Live Analysis', icon: Video },
  { path: '/history', label: 'History', icon: HistoryIcon },
];

export default function Sidebar() {
  const {
    isSupported,
    isListening,
    enabled,
    isActivating,
    activateVoice,
    deactivateVoice,
    engine,
    lastCommand,
    heardText,
    error,
    isPreparing,
  } = useVoiceCommands();

  const voiceButtonDisabled = isPreparing || isActivating;
  const voiceButtonLabel = isPreparing
    ? 'Przygotowuję głos…'
    : isActivating
      ? 'Proszę o mikrofon…'
      : enabled
        ? 'Wyłącz głos'
        : 'Włącz sterowanie głosem';

  return (
    <aside className="w-64 h-full glass-card border-r border-white/5 flex flex-col p-4 overflow-y-auto shrink-0">
      <div className="flex items-center gap-3 mb-4 px-2 mt-2 shrink-0">
        <div className="w-10 h-10 rounded-lg bg-primary-container/20 flex items-center justify-center neon-glow">
          <Dumbbell className="w-6 h-6 text-primary" />
        </div>
        <h1 className="text-xl font-bold font-h1 tracking-wider text-primary">Cyber Trener</h1>
      </div>

      <div className="mb-5 px-1 shrink-0">
        <button
          type="button"
          disabled={voiceButtonDisabled}
          onClick={() => {
            if (enabled) deactivateVoice();
            else void activateVoice();
          }}
          className={cn(
            'w-full flex items-center justify-center gap-2 px-4 py-3.5 rounded-xl font-bold text-sm transition-all shadow-lg',
            enabled
              ? 'bg-error text-white hover:bg-error/90'
              : 'bg-primary text-surface hover:bg-primary-container',
            voiceButtonDisabled && 'opacity-70 cursor-wait',
          )}
        >
          {isPreparing || isActivating ? (
            <Loader2 className="w-5 h-5 animate-spin shrink-0" />
          ) : enabled && isListening ? (
            <Mic className="w-5 h-5 shrink-0" />
          ) : (
            <MicOff className="w-5 h-5 shrink-0" />
          )}
          <span>{voiceButtonLabel}</span>
        </button>
        {!enabled && !isPreparing && (
          <p className="text-xs text-on-surface-variant mt-2 px-1 text-center leading-relaxed">
            Kliknij — przeglądarka poprosi o mikrofon
          </p>
        )}
        {error && (
          <div className="mt-3 rounded-lg border border-error/40 bg-error/10 px-3 py-2">
            <p className="text-xs font-semibold text-error mb-1">Blad glosu</p>
            <p className="text-xs text-error/90 leading-relaxed break-words">{error}</p>
          </div>
        )}
      </div>

      <nav className="flex flex-col gap-2 shrink-0">
        {navItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            className={({ isActive }) => cn(
              'flex items-center gap-3 px-4 py-3 rounded-lg transition-all duration-300',
              'hover:bg-white/5',
              isActive ? 'bg-primary/10 text-primary border border-primary/20 neon-glow' : 'text-on-surface-variant',
            )}
          >
            <item.icon className="w-5 h-5" />
            <span className="font-medium font-body-lg">{item.label}</span>
          </NavLink>
        ))}
      </nav>

      <div className="mt-auto pt-6 px-1 space-y-3 shrink-0">
        {enabled && (
          <div className="bg-surface-variant/50 rounded-xl p-4 border border-primary/20 text-sm">
            <p className="text-on-surface-variant mb-2">Nasłuch</p>
            <div className="flex items-center gap-2 mb-2">
              <div
                className={cn(
                  'w-2 h-2 rounded-full',
                  isListening
                    ? 'bg-primary shadow-[0_0_8px_rgba(0,229,255,0.6)] ai-pulse'
                    : 'bg-amber-400',
                )}
              />
              <span className="text-white font-medium text-xs">
                {isListening
                  ? engine === 'vosk'
                    ? 'Aktywny (Vosk)'
                    : 'Aktywny'
                  : 'Łączenie…'}
              </span>
            </div>
            <p className="text-xs text-on-surface-variant leading-relaxed">
              „rozpocznij”, „zatrzymaj”, „panel”, „analiza”
            </p>
            {heardText && (
              <p className="text-xs text-on-surface-variant mt-2 break-words" title={heardText}>
                Słyszę: „{heardText}”
              </p>
            )}
            {lastCommand && (
              <p className="text-xs text-primary mt-2">Wykonano: {VOICE_COMMAND_LABELS[lastCommand]}</p>
            )}
          </div>
        )}

        {!isSupported && !enabled && (
          <p className="text-xs text-amber-300/90 text-center">
            Do głosu potrzebny backend: port 8000
          </p>
        )}

        <div className="bg-surface-variant/50 rounded-xl p-4 border border-white/5 text-sm">
          <p className="text-on-surface-variant mb-2">System Status</p>
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.6)]" />
            <span className="text-green-400 font-medium text-xs">Operational</span>
          </div>
        </div>
      </div>
    </aside>
  );
}
