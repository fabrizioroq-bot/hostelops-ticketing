import { Navigate, Outlet } from "react-router-dom";
import { Center, Loader } from "@mantine/core";
import { useAuth } from "../hooks/useAuth";
import { useInactivityLogout } from "../hooks/useInactivityLogout";
import type { UserRole } from "../types";

export function ProtectedRoute({ allowedRoles }: { allowedRoles?: UserRole[] }) {
  const { session, profile, loading } = useAuth();
  useInactivityLogout();

  if (loading) {
    return (
      <Center h="100vh">
        <Loader />
      </Center>
    );
  }

  if (!session) {
    return <Navigate to="/login" replace />;
  }

  if (!profile) {
    // Session exists but /auth/me hasn't resolved yet (or the profile is
    // missing/deactivated) — avoid flashing protected content.
    return (
      <Center h="100vh">
        <Loader />
      </Center>
    );
  }

  if (allowedRoles && !allowedRoles.includes(profile.role)) {
    // "/dashboard" isn't a real route — go through "/" so
    // DefaultLandingRedirect can send this role somewhere it's actually
    // allowed (avoids landing on a 404 or bouncing between blocked pages).
    return <Navigate to="/" replace />;
  }

  return <Outlet />;
}
