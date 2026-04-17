import { useIsAuthenticated, useMsal } from "@azure/msal-react";
import { InteractionStatus } from "@azure/msal-browser";
import { loginRequest } from "./authConfig";
import LoginPage from "./pages/LoginPage";
import AppShell from "./components/Layout/AppShell";
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

  return <AppShell />;
}
