import { Component, type ErrorInfo, type ReactNode } from "react";

interface Props {
  children: ReactNode;
  /** Optional label shown in the error card, e.g. "Incident Detail" */
  section?: string;
  /** If true, render a small inline error instead of a full card */
  inline?: boolean;
}

interface State {
  error: Error | null;
}

export default class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("[ErrorBoundary]", this.props.section ?? "unknown section", error, info);
  }

  reset = () => this.setState({ error: null });

  render() {
    const { error } = this.state;
    if (!error) return this.props.children;

    const label = this.props.section ?? "This section";

    if (this.props.inline) {
      return (
        <div className="error-inline">
          ⚠️ {label} failed to load.{" "}
          <button className="link-button" onClick={this.reset}>
            Retry
          </button>
        </div>
      );
    }

    return (
      <div className="error-card">
        <h2 className="error-card-title">⚠️ {label} encountered an error</h2>
        <p className="error-card-message">{error.message}</p>
        <div className="error-card-actions">
          <button className="btn btn--secondary" onClick={this.reset}>
            Try again
          </button>
          <button
            className="btn btn--secondary"
            onClick={() => window.location.assign("/")}
          >
            Go to Dashboard
          </button>
        </div>
      </div>
    );
  }
}
