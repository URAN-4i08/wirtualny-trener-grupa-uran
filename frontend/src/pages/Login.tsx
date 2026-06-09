import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Mail, Lock, LogIn } from 'lucide-react';
import { isSupabaseConfigured, supabase } from '../config/supabase';
import AuthShell from '../components/layout/AuthShell';

export default function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  async function handleLogin(event: React.FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError(null);

    if (!isSupabaseConfigured) {
      setError('Brakuje konfiguracji Supabase. Dodaj plik frontend/.env z adresem projektu i kluczem anon.');
      setLoading(false);
      return;
    }

    const { error: loginError } = await supabase.auth.signInWithPassword({ email, password });

    if (loginError) {
      setError(loginError.message || 'Nie udało się zalogować. Sprawdź email i hasło.');
    } else {
      navigate('/dashboard');
    }

    setLoading(false);
  }

  return (
    <AuthShell
      title="Witaj ponownie"
      subtitle="Zaloguj się do swojego panelu zawodnika"
      footerLink={{ prompt: 'Nie masz jeszcze konta?', label: 'Załóż konto', to: '/register' }}
    >
      {!isSupabaseConfigured && (
        <div className="rounded-lg border border-amber-500/40 bg-amber-500/10 px-4 py-3 text-sm text-amber-200">
          Brakuje konfiguracji Supabase w pliku frontend/.env.
        </div>
      )}
      {error && (
        <div className="rounded-lg border border-error/40 bg-error/10 px-4 py-3 text-sm text-error">{error}</div>
      )}
      <form className="space-y-5" onSubmit={handleLogin}>
        <div className="space-y-2">
          <label className="ml-1 text-xs font-semibold uppercase tracking-wide text-on-surface-variant" htmlFor="email">
            Adres e-mail
          </label>
          <div className="relative">
            <Mail className="absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-outline" />
            <input
              id="email"
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="email@przyklad.pl"
              className="w-full rounded-xl border-none bg-surface-container-high py-3.5 pl-12 pr-4 text-on-surface placeholder:text-outline/50 focus:ring-2 focus:ring-primary"
            />
          </div>
        </div>
        <div className="space-y-2">
          <label className="ml-1 text-xs font-semibold uppercase tracking-wide text-on-surface-variant" htmlFor="password">
            Hasło
          </label>
          <div className="relative">
            <Lock className="absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-outline" />
            <input
              id="password"
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              className="w-full rounded-xl border-none bg-surface-container-high py-3.5 pl-12 pr-4 text-on-surface placeholder:text-outline/50 focus:ring-2 focus:ring-primary"
            />
          </div>
        </div>
        <button type="submit" disabled={loading} className="btn-primary flex w-full items-center justify-center gap-2 disabled:opacity-60">
          <span>{loading ? 'Logowanie...' : 'Zaloguj się'}</span>
          <LogIn className="h-5 w-5" />
        </button>
      </form>
    </AuthShell>
  );
}
