import { Link } from 'react-router-dom';

export default function AppFooter({ compact = false }: { compact?: boolean }) {
  return (
    <footer className="mt-auto border-t border-white/5 bg-surface-container-lowest/80 py-4">
      <div className="mx-auto flex max-w-container flex-col items-center justify-between gap-3 px-6 text-xs text-on-surface-variant md:flex-row">
        <span>Realizacja: Zespół Cyber-Trener</span>
        {!compact && (
          <span className="text-center text-[11px] leading-relaxed md:text-left">
            Grupa Uran — Szymon Zamachowski 255735 · Piotr Michalak 255654 · Krzysztof Olbiński 255667 ·
            Dominik Kwintal 255647
          </span>
        )}
        <div className="flex gap-4">
          <Link to="/voice-commands" className="transition-colors hover:text-primary">
            Komendy głosowe
          </Link>
        </div>
      </div>
    </footer>
  );
}
