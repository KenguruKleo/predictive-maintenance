import { useSignalR } from "../../hooks/useSignalR";
import { useInfiniteActiveIncidents } from "../../hooks/useIncidents";

export default function AppFooter() {
  const { connected } = useSignalR();
  const { data } = useInfiniteActiveIncidents(1);
  const total = data?.pages[0]?.total ?? null;

  return (
    <footer className="app-footer">
      <div className="app-footer-left">
        {connected ? (
          <span className="footer-status footer-status--online">
            <span className="footer-status-dot" /> Live
          </span>
        ) : (
          <span className="footer-status footer-status--offline">
            <span className="footer-status-dot" /> Offline
          </span>
        )}
      </div>
      <div className="app-footer-right">
        {total !== null && (
          <span className="footer-incidents">
            <span className="footer-incidents-count">{total}</span>
            {" "}active incident{total !== 1 ? "s" : ""}
          </span>
        )}
      </div>
    </footer>
  );
}
