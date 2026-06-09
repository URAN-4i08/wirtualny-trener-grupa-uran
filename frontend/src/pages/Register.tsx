import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Mail, Lock, User, UserPlus } from 'lucide-react';
import { isSupabaseConfigured, supabase } from '../config/supabase';
import AuthShell from '../components/layout/AuthShell';

export default function Register() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [firstName, setFirstName] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const navigate = useNavigate();

  async function handleRegister(event: React.FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError(null);

    if (!isSupabaseConfigured) {
      setError('Brakuje konfiguracji Supabase. Dodaj plik frontend/.env z adresem projektu i kluczem anon.');
      setLoading(false);
      return;
    }

    const { error: registerError } = await supabase.auth.signUp({
      email,
      password,
      options: { data: { first_name: firstName } },
    });

    if (registerError) {
      setError(registerError.message || 'Nie udało się utworzyć konta.');
      setLoading(false);
      return;
    }

    setSuccess(true);
    setLoading(false);
    window.setTimeout(() => navigate('/login'), 3000);
  }

  return (
    <AuthShell
      title="Utwórz konto"
      subtitle="Rozpocznij treningi z własnym profilem"
      footerLink={{ prompt: 'Masz już konto?', label: 'Zaloguj się', to: '/login' }}
    >
      {success ? (
        <div className="rounded-lg border border-success/40 bg-success/10 px-4 py-3 text-center text-success">
          Rejestracja przebiegła pomyślnie. Za chwilę wrócisz do logowania.
        </div>
      ) : (
        <form className="space-y-5" onSubmit={handleRegister}>
          {error && (
            <div className="rounded-lg border border-error/40 bg-error/10 px-4 py-3 text-sm text-error">{error}</div>
          )}
          <div className="space-y-2">
            <label className="ml-1 text-xs font-semibold uppercase tracking-wide text-on-surface-variant" htmlFor="firstName">
              Imię
            </label>
            <div className="relative">
              <User className="absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-outline" />
              <input
                id="firstName"
                type="text"
                required
                value={firstName}
                onChange={(e) => setFirstName(e.target.value)}
                className="w-full rounded-xl border-none bg-surface-container-high py-3.5 pl-12 pr-4 text-on-surface focus:ring-2 focus:ring-primary"
                placeholder="Twoje imię"
              />
            </div>
          </div>
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
                className="w-full rounded-xl border-none bg-surface-container-high py-3.5 pl-12 pr-4 text-on-surface focus:ring-2 focus:ring-primary"
                placeholder="twoj@email.com"
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
                minLength={6}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full rounded-xl border-none bg-surface-container-high py-3.5 pl-12 pr-4 text-on-surface focus:ring-2 focus:ring-primary"
                placeholder="••••••••"
              />
            </div>
          </div>
          <button type="submit" disabled={loading} className="btn-primary flex w-full items-center justify-center gap-2 disabled:opacity-60">
            <span>{loading ? 'Tworzenie konta...' : 'Zarejestruj się'}</span>
            <UserPlus className="h-5 w-5" />
          </button>
        </form>
      )}
    </AuthShell>
  );
}
