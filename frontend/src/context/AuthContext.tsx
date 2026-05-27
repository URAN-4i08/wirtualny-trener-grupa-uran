import React, { createContext, useContext, useEffect, useState } from 'react';
import type { User } from '@supabase/supabase-js';
import { supabase } from '../config/supabase';

export type UserProfile = {
  id: string;
  first_name: string | null;
  last_name: string | null;
  avatar_url: string | null;
  experience_level: string | null;
};

interface AuthContextType {
  user: User | null;
  profile: UserProfile | null;
  displayName: string;
  loading: boolean;
  signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  profile: null,
  displayName: 'Trenerze',
  loading: true,
  signOut: async () => {},
});

export const useAuth = () => useContext(AuthContext);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadProfile(currentUser: User | null) {
      if (!currentUser) {
        setProfile(null);
        return;
      }

      const { data, error } = await supabase
        .from('profiles')
        .select('id, first_name, last_name, avatar_url, experience_level')
        .eq('id', currentUser.id)
        .maybeSingle();

      if (error) {
        console.error('Błąd pobierania profilu:', error);
        setProfile(null);
        return;
      }

      setProfile(data as UserProfile | null);
    }

    supabase.auth.getSession()
      .then(async ({ data: { session } }) => {
        const currentUser = session?.user ?? null;
        setUser(currentUser);
        await loadProfile(currentUser);
        setLoading(false);
      })
      .catch((err) => {
        console.error('Błąd sesji Supabase:', err);
        setLoading(false);
      });

    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      const currentUser = session?.user ?? null;
      setUser(currentUser);
      void loadProfile(currentUser);
    });

    return () => subscription.unsubscribe();
  }, []);

  const signOut = async () => {
    await supabase.auth.signOut();
    setProfile(null);
  };

  const firstName =
    profile?.first_name ||
    (typeof user?.user_metadata?.first_name === 'string' ? user.user_metadata.first_name : '');
  const displayName = firstName?.trim() || 'Trenerze';

  return (
    <AuthContext.Provider value={{ user, profile, displayName, loading, signOut }}>
      {loading ? (
        <div className="flex h-screen w-full items-center justify-center bg-zinc-950 text-white">
          <p>Ładowanie aplikacji...</p>
        </div>
      ) : children}
    </AuthContext.Provider>
  );
};
