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
import TemplateManagementPage from "./pages/TemplateManagementPage";
import NotFoundPage from "./pages/NotFoundPage";
import "./App.css";

export default function App() {
  const isAuthenticated = useIsAuthenticated();
  const { inProgress } = useMsal();

  if (inProgress !== InteractionStatus.None) {
    return (
      <div className="loading-screen">
        <div className="spinner" />
        <p>Authenticating…</p>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <LoginPage loginRequest={loginRequest} />;
  }

  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppShell />}>
          <Route index element={<OperationsDashboard />} />
          <Route path="incidents/:id" element={<IncidentDetailPage />} />
          <Route path="history" element={<IncidentHistoryPage />} />
          <Route path="manager" element={<ManagerDashboardPage />} />
          <Route path="templates" element={<TemplateManagementPage />} />
          <Route path="login" element={<Navigate to="/" replace />} />
          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
