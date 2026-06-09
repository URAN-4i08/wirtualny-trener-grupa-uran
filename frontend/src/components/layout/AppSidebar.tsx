import { NavLink, Link } from 'react-router-dom';
import {
  LayoutDashboard,
  Flame,
  Video,
  History,
  Mic,
  MicOff,
  Loader2,
  ChevronLeft,
  ChevronRight,
  User,
} from 'lucide-react';
import { clsx } from 'clsx';
import Logo from '../Logo';
import { useAuth } from '../../context/AuthContext';
import { useVoiceCommands, VOICE_COMMAND_LABELS } from '../../context/VoiceCommandContext';

const navItems = [
  { path: '/dashboard', label: 'Panel główny', icon: LayoutDashboard },
  { path: '/warmup', label: 'Rozgrzewka', icon: Flame },
  { path: '/live', label: 'Analiza', icon: Video },
  { path: '/history', label: 'Historia', icon: History },
];

type AppSidebarProps = {
  collapsed: boolean;
  onToggleCollapse: () => void;
};

export default function AppSidebar({ collapsed, onToggleCollapse }: AppSidebarProps) {
  const { displayName, signOut } = useAuth();
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

  const voiceDisabled = isPreparing || isActivating;

  return (
    <aside
      className={clsx(
        'fixed left-0 top-0 z-40 flex h-full flex-col border-r border-white/10 bg-surface/90 py-6 backdrop-blur-xl transition-all duration-300',
        collapsed ? 'w-sidebar-collapsed' : 'w-sidebar',
      )}
    >
      <div className={clsx('mb-8 flex items-center gap-3', collapsed ? 'justify-center px-2' : 'px-6')}>
        <Logo size={40} />
        {!collapsed && (
          <div className="min-w-0">
            <p className="font-display text-lg font-bold leading-tight text-primary">Cyber-Trener</p>
            <p className="text-sm text-on-surface-variant">Siatkarz</p>
          </div>
        )}
      </div>

      <nav className="flex flex-1 flex-col gap-1 px-2">
        {navItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            title={collapsed ? item.label : undefined}
            className={({ isActive }) =>
              clsx(
                'flex items-center gap-3 rounded-lg py-3 transition-colors',
                collapsed ? 'justify-center px-2' : 'px-4',
                isActive
                  ? 'nav-active'
                  : 'text-on-surface-variant hover:bg-white/5 hover:text-on-surface',
              )
            }
          >
            <item.icon className="h-5 w-5 shrink-0" />
            {!collapsed && <span className="font-medium">{item.label}</span>}
          </NavLink>
        ))}
      </nav>

      <div className={clsx('space-y-3 px-2', collapsed ? 'px-2' : 'px-4')}>
        <button
          type="button"
          disabled={voiceDisabled}
          onClick={() => {
            if (enabled) deactivateVoice();
            else void activateVoice();
          }}
          title={collapsed ? 'Sterowanie głosowe' : undefined}
          className={clsx(
            'flex w-full items-center justify-center gap-2 rounded-xl py-3 text-sm font-semibold transition-all',
            enabled ? 'bg-error/90 text-white' : 'bg-primary-container text-on-primary-container hover:brightness-110',
            voiceDisabled && 'cursor-wait opacity-70',
            collapsed && 'px-0',
          )}
        >
          {isPreparing || isActivating ? (
            <Loader2 className="h-5 w-5 animate-spin" />
          ) : enabled && isListening ? (
            <Mic className="h-5 w-5" />
          ) : (
            <MicOff className="h-5 w-5" />
          )}
          {!collapsed && <span>{enabled ? 'Wyłącz głos' : 'Sterowanie głosowe'}</span>}
        </button>

        {!collapsed && enabled && (
          <div className="glass-panel rounded-xl p-3 text-xs">
            <p className="mb-1 text-on-surface-variant">Nasłuch {engine === 'vosk' ? '(Vosk)' : ''}</p>
            {heardText && <p className="truncate text-on-surface">Słyszę: „{heardText}"</p>}
            {lastCommand && <p className="mt-1 text-primary">Wykonano: {VOICE_COMMAND_LABELS[lastCommand]}</p>}
          </div>
        )}

        {!collapsed && error && (
          <p className="rounded-lg border border-error/30 bg-error/10 px-3 py-2 text-xs text-error">{error}</p>
        )}

        {!collapsed && !isSupported && !enabled && (
          <p className="text-center text-xs text-amber-300/90">Do głosu potrzebny jest lokalny backend.</p>
        )}

        {!collapsed && (
          <Link
            to="/voice-commands"
            className="block px-2 text-xs text-on-surface-variant transition-colors hover:text-primary"
          >
            Komendy głosowe →
          </Link>
        )}

        <div className="border-t border-white/5 pt-4">
          <div className={clsx('flex items-center gap-3', collapsed && 'justify-center')}>
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-primary-container/20 text-primary">
              <User className="h-5 w-5" />
            </div>
            {!collapsed && (
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium text-on-surface">{displayName}</p>
                <button
                  type="button"
                  onClick={() => void signOut()}
                  className="text-xs text-error transition-colors hover:text-error/80"
                >
                  Wyloguj się
                </button>
              </div>
            )}
          </div>
        </div>

        <button
          type="button"
          onClick={onToggleCollapse}
          className="flex w-full items-center justify-center rounded-lg py-2 text-on-surface-variant transition-colors hover:bg-white/5 hover:text-on-surface"
          aria-label={collapsed ? 'Rozwiń menu' : 'Zwiń menu'}
        >
          {collapsed ? <ChevronRight className="h-5 w-5" /> : <ChevronLeft className="h-5 w-5" />}
        </button>
      </div>
    </aside>
  );
}
