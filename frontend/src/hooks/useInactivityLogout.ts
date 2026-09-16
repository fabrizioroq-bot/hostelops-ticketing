import { useEffect, useRef } from "react";
import { useAuth } from "./useAuth";

const TIMEOUT_MS = 30 * 60 * 1000; // 30 minutes, per the security requirement
const ACTIVITY_EVENTS: (keyof WindowEventMap)[] = [
  "mousedown", "mousemove", "keydown", "scroll", "touchstart",
];

/** Signs the user out after 30 minutes with no interaction, regardless of
 * whether their Supabase access token is still technically valid. */
export function useInactivityLogout() {
  const { session, signOut } = useAuth();
  const timerRef = useRef<number | undefined>(undefined);

  useEffect(() => {
    if (!session) return;

    const reset = () => {
      window.clearTimeout(timerRef.current);
      timerRef.current = window.setTimeout(() => {
        signOut();
      }, TIMEOUT_MS);
    };

    reset();
    ACTIVITY_EVENTS.forEach((evt) => window.addEventListener(evt, reset));

    return () => {
      window.clearTimeout(timerRef.current);
      ACTIVITY_EVENTS.forEach((evt) => window.removeEventListener(evt, reset));
    };
  }, [session, signOut]);
}
