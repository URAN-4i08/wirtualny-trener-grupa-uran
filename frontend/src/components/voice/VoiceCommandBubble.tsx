import { clsx } from 'clsx';
import { Mic, Sparkles } from 'lucide-react';
import { VOICE_COMMAND_LABELS, type VoiceCommandId } from '../../voice/commandParser';

type VoiceCommandBubbleProps = {
  heardText: string | null;
  lastCommand: VoiceCommandId | null;
  isListening: boolean;
  enabled: boolean;
  className?: string;
};

export default function VoiceCommandBubble({
  heardText,
  lastCommand,
  isListening,
  enabled,
  className,
}: VoiceCommandBubbleProps) {
  if (!enabled) return null;

  const showHeard = Boolean(heardText);
  const showCommand = Boolean(lastCommand);

  if (!showHeard && !showCommand && !isListening) return null;

  return (
    <div
      className={clsx(
        'absolute left-1/2 bottom-20 max-w-[92%] -translate-x-1/2 rounded-full border px-5 py-2.5 shadow-lg backdrop-blur-md',
        showCommand
          ? 'border-primary-container/50 bg-primary-container/25 text-on-surface'
          : 'border-white/20 bg-black/40 text-on-surface',
        className,
      )}
    >
      <div className="flex items-center gap-2">
        {showCommand ? (
          <Sparkles className="h-5 w-5 shrink-0 text-primary-container" />
        ) : (
          <Mic className={clsx('h-5 w-5 shrink-0', isListening ? 'text-success pulse-live' : 'text-on-surface-variant')} />
        )}
        <span className="font-display text-sm font-bold md:text-base">
          {showCommand ? (
            <>Wykonano: {VOICE_COMMAND_LABELS[lastCommand!]}</>
          ) : showHeard ? (
            <>„{heardText}"</>
          ) : (
            'Nasłuchuję komend...'
          )}
        </span>
      </div>
    </div>
  );
}
