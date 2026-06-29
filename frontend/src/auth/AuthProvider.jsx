import React, { createContext, useContext, useEffect, useMemo, useState } from "react";
import { supabase } from "../supabaseClient.js";

const AuthContext = createContext(null);

export function useAuth() {
  return useContext(AuthContext);
}

export function AuthProvider({ children }) {
  const [session, setSession] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;

    supabase.auth.getSession().then(({ data }) => {
      if (!mounted) return;
      setSession(data.session);
      setLoading(false);
    });

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, nextSession) => {
      setSession(nextSession);
      setLoading(false);
    });

    // `api.js` dispatches this after refresh failure so protected routes update
    // immediately instead of waiting for Supabase storage listeners.
    function handleAuthExpired() {
      setSession(null);
      setLoading(false);
    }

    window.addEventListener("lexio:auth-expired", handleAuthExpired);

    return () => {
      mounted = false;
      window.removeEventListener("lexio:auth-expired", handleAuthExpired);
      subscription.unsubscribe();
    };
  }, []);

  const value = useMemo(() => {
    return { session, user: session?.user || null, loading };
  }, [session, loading]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
