import { useState } from "react";
import { useIncidents } from "../hooks/useIncidents";
import Filters from "../components/IncidentList/Filters";
import IncidentTable from "../components/IncidentList/IncidentTable";
import type { IncidentStatus, Severity } from "../types/incident";

export default function IncidentHistoryPage() {
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState<IncidentStatus | "">("");
  const [severity, setSeverity] = useState<Severity | "">("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [page, setPage] = useState(1);

  const { data, isLoading } = useIncidents({
    search: search || undefined,
    status: status || undefined,
    severity: severity || undefined,
    date_from: dateFrom || undefined,
    date_to: dateTo ? dateTo + "T23:59:59Z" : undefined,
    page,
    page_size: 20,
  });

  const incidents = data?.items ?? [];
  const total = data?.total ?? 0;
  const totalPages = Math.ceil(total / 20);

  const resetPage = () => setPage(1);

  return (
    <div className="page-history">
      <h1 className="page-title">Incident History & Audit</h1>

      <Filters
        search={search}
        onSearchChange={(v) => { setSearch(v); resetPage(); }}
        status={status}
        onStatusChange={(v) => { setStatus(v); resetPage(); }}
        severity={severity}
        onSeverityChange={(v) => { setSeverity(v); resetPage(); }}
        dateFrom={dateFrom}
        onDateFromChange={(v) => { setDateFrom(v); resetPage(); }}
        dateTo={dateTo}
        onDateToChange={(v) => { setDateTo(v); resetPage(); }}
      />

      <div className="history-meta">
        Showing {incidents.length} of {total} incidents
      </div>

      {isLoading ? (
        <div className="loading">Loading...</div>
      ) : (
        <IncidentTable incidents={incidents} />
      )}

      {totalPages > 1 && (
        <div className="pagination">
          <button
            className="btn btn--secondary"
            disabled={page <= 1}
            onClick={() => setPage((p) => p - 1)}
          >
            ← Prev
          </button>
          <span className="pagination-info">
            Page {page} of {totalPages}
          </span>
          <button
            className="btn btn--secondary"
            disabled={page >= totalPages}
            onClick={() => setPage((p) => p + 1)}
          >
            Next →
          </button>
        </div>
      )}
    </div>
  );
}
