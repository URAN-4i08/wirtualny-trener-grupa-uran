import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { isSupabaseConfigured, supabase } from '../config/supabase';
import { Activity, Mail, Lock, User } from 'lucide-react';

const Register: React.FC = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [firstName, setFirstName] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const navigate = useNavigate();

  const handleRegister = async (event: React.FormEvent) => {
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
      options: {
        data: {
          first_name: firstName,
        },
      },
    });

    if (registerError) {
      setError(registerError.message || 'Nie udało się utworzyć konta. Sprawdź dane i spróbuj ponownie.');
      setLoading(false);
      return;
    }

    setSuccess(true);
    setLoading(false);
    window.setTimeout(() => navigate('/login'), 3000);
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-zinc-950 p-4">
      <div className="max-w-md w-full space-y-8 bg-zinc-900 p-8 rounded-xl border border-zinc-800 shadow-2xl">
        <div className="text-center">
          <Activity className="mx-auto h-12 w-12 text-primary" />
          <h2 className="mt-6 text-3xl font-bold text-white">Utwórz konto</h2>
          <p className="mt-2 text-sm text-zinc-400">Rozpocznij treningi z własnym profilem.</p>
        </div>

        {success ? (
          <div className="bg-green-500/10 border border-green-500/50 text-green-400 rounded-lg p-4 text-center">
            Rejestracja przebiegła pomyślnie. Za chwilę wrócisz do logowania.
          </div>
        ) : (
          <form className="mt-8 space-y-6" onSubmit={handleRegister}>
            {!isSupabaseConfigured && (
              <div className="bg-amber-500/10 border border-amber-500/50 text-amber-200 rounded-lg p-3 text-sm text-center">
                Brakuje konfiguracji Supabase w pliku frontend/.env.
              </div>
            )}
            {error && (
              <div className="bg-red-500/10 border border-red-500/50 text-red-400 rounded-lg p-3 text-sm text-center">
                {error}
              </div>
            )}
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-zinc-300">Imię</label>
                <div className="mt-1 relative">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                    <User className="h-5 w-5 text-zinc-500" />
                  </div>
                  <input
                    type="text"
                    required
                    value={firstName}
                    onChange={(event) => setFirstName(event.target.value)}
                    className="block w-full pl-10 pr-3 py-2 border border-zinc-700 rounded-lg bg-zinc-800 text-white placeholder-zinc-400 focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent transition"
                    placeholder="Twoje imię"
                  />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-zinc-300">Email</label>
                <div className="mt-1 relative">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                    <Mail className="h-5 w-5 text-zinc-500" />
                  </div>
                  <input
                    type="email"
                    required
                    value={email}
                    onChange={(event) => setEmail(event.target.value)}
                    className="block w-full pl-10 pr-3 py-2 border border-zinc-700 rounded-lg bg-zinc-800 text-white placeholder-zinc-400 focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent transition"
                    placeholder="twoj@email.com"
                  />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-zinc-300">Hasło</label>
                <div className="mt-1 relative">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                    <Lock className="h-5 w-5 text-zinc-500" />
                  </div>
                  <input
                    type="password"
                    required
                    minLength={6}
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                    className="block w-full pl-10 pr-3 py-2 border border-zinc-700 rounded-lg bg-zinc-800 text-white placeholder-zinc-400 focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent transition"
                    placeholder="••••••••"
                  />
                </div>
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full flex justify-center py-3 px-4 border border-transparent rounded-lg shadow-sm text-sm font-medium text-surface bg-primary hover:bg-primary/90 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary focus:ring-offset-zinc-900 transition disabled:opacity-50"
            >
              {loading ? 'Tworzenie konta...' : 'Zarejestruj się'}
            </button>
          </form>
        )}
        <div className="text-center text-sm text-zinc-400">
          Masz już konto?{' '}
          <Link to="/login" className="font-medium text-primary hover:text-primary/80 transition">
            Zaloguj się
          </Link>
        </div>
      </div>
    </div>
  );
};

export default Register;
