import { useIsAuthenticated, useMsal } from "@azure/msal-react";
import { InteractionStatus } from "@azure/msal-browser";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { loginRequest } from "./authConfig";
import LoginPage from "./pages/LoginPage";
import AppShell from "./components/Layout/AppShell";
import OperationsDashboard from "./pages/OperationsDashboard";
import IncidentDetailPage from "./pages/IncidentDetailPage";
import IncidentHistoryPage from "./pages/IncidentHistoryPage";
import ManagerDashboardPage from "./pages/ManagerDashboardPage";
import IncidentTelemetryPage from "./pages/IncidentTelemetryPage";
import TemplateManagementPage from "./pages/TemplateManagementPage";
import NotFoundPage from "./pages/NotFoundPage";
import ErrorBoundary from "./components/ErrorBoundary";
import { IS_E2E_AUTH } from "./authRuntime";
import "./App.css";

export default function App() {
  const isAuthenticated = useIsAuthenticated();
  const { inProgress } = useMsal();

  if (!IS_E2E_AUTH && inProgress !== InteractionStatus.None) {
    return (
      <div className="loading-screen">
        <div className="spinner" />
        <p>Authenticating…</p>
      </div>
    );
  }

  if (!IS_E2E_AUTH && !isAuthenticated) {
    return <LoginPage loginRequest={loginRequest} />;
  }

  return (
    <BrowserRouter>
      <ErrorBoundary section="Application">
        <Routes>
          <Route element={<AppShell />}>
            <Route index element={
              <ErrorBoundary section="Operations Dashboard">
                <OperationsDashboard />
              </ErrorBoundary>
            } />
            <Route path="incidents/:id" element={
              <ErrorBoundary section="Incident Detail">
                <IncidentDetailPage />
              </ErrorBoundary>
            } />
            <Route path="history" element={
              <ErrorBoundary section="Incident History">
                <IncidentHistoryPage />
              </ErrorBoundary>
            } />
            <Route path="manager" element={
              <ErrorBoundary section="Manager Dashboard">
                <ManagerDashboardPage />
              </ErrorBoundary>
            } />
            <Route path="telemetry" element={
              <ErrorBoundary section="Incident Telemetry">
                <IncidentTelemetryPage />
              </ErrorBoundary>
            } />
            <Route path="templates" element={
              <ErrorBoundary section="Template Management">
                <TemplateManagementPage />
              </ErrorBoundary>
            } />
            <Route path="login" element={<Navigate to="/" replace />} />
            <Route path="*" element={<NotFoundPage />} />
          </Route>
        </Routes>
      </ErrorBoundary>
    </BrowserRouter>
  );
}
