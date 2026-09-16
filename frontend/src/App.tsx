import { Navigate, Route, Routes } from "react-router-dom";

import { ProtectedRoute } from "./components/ProtectedRoute";
import { AppLayout } from "./components/AppLayout";
import { useAuth } from "./hooks/useAuth";

import { LoginPage } from "./pages/LoginPage";
import { ExecutiveDashboardPage } from "./pages/ExecutiveDashboardPage";
import { AgentDashboardPage } from "./pages/AgentDashboardPage";
import { DataQualityDashboardPage } from "./pages/DataQualityDashboardPage";
import { HostelPerformancePage } from "./pages/HostelPerformancePage";
import { TicketsListPage } from "./pages/TicketsListPage";
import { TicketDetailPage } from "./pages/TicketDetailPage";
import { TicketCreatePage } from "./pages/TicketCreatePage";
import { GuestsListPage } from "./pages/GuestsListPage";
import { GuestDetailPage } from "./pages/GuestDetailPage";
import { DedupReviewPage } from "./pages/DedupReviewPage";
import { HostelsPage } from "./pages/HostelsPage";
import { UsersPage } from "./pages/UsersPage";
import { ExportsPage } from "./pages/ExportsPage";
import { MaintenanceListPage } from "./pages/MaintenanceListPage";
import { MaintenanceCreatePage } from "./pages/MaintenanceCreatePage";
import { MaintenanceDetailPage } from "./pages/MaintenanceDetailPage";
import { NotFoundPage } from "./pages/NotFoundPage";

/** Maintenance-role users land in the Maintenance module; everyone else
 * lands on their personal dashboard. */
function DefaultLandingRedirect() {
  const { profile } = useAuth();
  return <Navigate to={profile?.role === "maintenance" ? "/maintenance" : "/dashboard/agent"} replace />;
}

export function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />

      <Route element={<ProtectedRoute />}>
        <Route element={<AppLayout />}>
          <Route path="/" element={<DefaultLandingRedirect />} />
        </Route>
      </Route>

      <Route element={<ProtectedRoute allowedRoles={["admin", "supervisor", "agent"]} />}>
        <Route element={<AppLayout />}>
          <Route path="/dashboard/agent" element={<AgentDashboardPage />} />
          <Route path="/tickets" element={<TicketsListPage />} />
          <Route path="/tickets/new" element={<TicketCreatePage />} />
          <Route path="/tickets/:ticketId" element={<TicketDetailPage />} />
          <Route path="/guests" element={<GuestsListPage />} />
          <Route path="/guests/:guestId" element={<GuestDetailPage />} />
          <Route path="/hostels" element={<HostelsPage />} />
        </Route>
      </Route>

      <Route element={<ProtectedRoute allowedRoles={["admin", "supervisor"]} />}>
        <Route element={<AppLayout />}>
          <Route path="/dashboard/executive" element={<ExecutiveDashboardPage />} />
          <Route path="/dashboard/hostel-performance" element={<HostelPerformancePage />} />
          <Route path="/dedup" element={<DedupReviewPage />} />
          <Route path="/exports" element={<ExportsPage />} />
        </Route>
      </Route>

      <Route element={<ProtectedRoute allowedRoles={["admin"]} />}>
        <Route element={<AppLayout />}>
          <Route path="/dashboard/data-quality" element={<DataQualityDashboardPage />} />
          <Route path="/users" element={<UsersPage />} />
        </Route>
      </Route>

      {/* Maintenance module — separate route group, separate role set
          (admin/supervisor view, maintenance-role creates/updates; agents
          have no access at all). */}
      <Route element={<ProtectedRoute allowedRoles={["admin", "supervisor", "maintenance"]} />}>
        <Route element={<AppLayout />}>
          <Route path="/maintenance" element={<MaintenanceListPage />} />
          <Route path="/maintenance/new" element={<MaintenanceCreatePage />} />
          <Route path="/maintenance/:ticketId" element={<MaintenanceDetailPage />} />
        </Route>
      </Route>

      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}
