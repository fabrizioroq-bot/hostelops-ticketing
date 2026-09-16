import { createClient } from "@supabase/supabase-js";

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY;

if (!supabaseUrl || !supabaseAnonKey) {
  throw new Error(
    "Missing VITE_SUPABASE_URL or VITE_SUPABASE_ANON_KEY. Copy .env.example to .env and fill them in."
  );
}

// Supabase JS persists the session in localStorage and auto-refreshes the
// access token before it expires. Combined with the Supabase Auth JWT
// expiry (set to 1800s / 30 min in the dashboard — see docs/DEPLOYMENT.md)
// and the inactivity-based sign-out in hooks/useInactivityLogout.ts, this
// gives the required 30-minute session timeout behavior.
export const supabase = createClient(supabaseUrl, supabaseAnonKey, {
  auth: {
    persistSession: true,
    autoRefreshToken: true,
    detectSessionInUrl: true,
  },
});
