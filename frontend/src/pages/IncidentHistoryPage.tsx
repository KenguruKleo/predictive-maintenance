import { useEffect, useRef } from "react";
import { useSearchParams } from "react-router-dom";
import { useInfiniteQuery } from "@tanstack/react-query";
import { getIncidents } from "../api/incidents";
import Filters from "../components/IncidentList/Filters";
import Breadcrumb from "../components/Layout/Breadcrumb";
import IncidentTable from "../components/IncidentList/IncidentTable";
import type { Incident, IncidentStatus, Severity } from "../types/incident";

function exportIncidentsToCSV(incidents: Incident[]): void {
  const columns: { header: string; value: (inc: Incident) => string }[] = [
    { header: "Incident ID", value: (i) => i.incident_number ?? i.id },
    { header: "Title", value: (i) => i.title ?? (i.parameter ? i.parameter.replace(/_/g, " ") : "") },
    { header: "Equipment", value: (i) => i.equipment_id },
    { header: "Severity", value: (i) => i.severity },
    { header: "Status", value: (i) => i.status },
    { header: "Batch ID", value: (i) => i.batch_id ?? "" },
    { header: "Deviation Type", value: (i) => i.deviation_type ?? "" },
    { header: "Parameter", value: (i) => i.parameter ?? "" },
    { header: "Measured Value", value: (i) => i.measured_value != null ? String(i.measured_value) : "" },
    { header: "Unit", value: (i) => i.unit ?? "" },
    { header: "Risk Level", value: (i) => i.ai_analysis?.risk_level ?? "" },
    { header: "AI Confidence", value: (i) => i.ai_analysis?.confidence != null ? String(i.ai_analysis.confidence) : "" },
    { header: "AI Recommendation", value: (i) => i.ai_analysis?.agent_recommendation ?? "" },
    { header: "Operator Agrees With AI", value: (i) => i.operatorAgreesWithAgent != null ? String(i.operatorAgreesWithAgent) : "" },
    { header: "Root Cause", value: (i) => i.ai_analysis?.root_cause_hypothesis ?? i.ai_analysis?.root_cause ?? "" },
    { header: "Assigned To", value: (i) => i.assigned_to ?? "" },
    { header: "Created At", value: (i) => i.created_at ?? i.reported_at ?? "" },
  ];

  const escape = (v: string) => `"${v.replace(/"/g, '""')}"`;
  const header = columns.map((c) => escape(c.header)).join(",");
  const rows = incidents.map((inc) =>
    columns.map((c) => escape(c.value(inc))).join(",")
  );
  const csv = [header, ...rows].join("\r\n");

  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  const date = new Date().toISOString().slice(0, 10);
  a.href = url;
  a.download = `incidents-audit-${date}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

const PAGE_SIZE = 20;

export default function IncidentHistoryPage() {
  const [searchParams, setSearchParams] = useSearchParams();

  // All filter state lives in the URL — read directly from params
  const equipmentId = searchParams.get("equipment_id") ?? "";
  const search = searchParams.get("search") ?? "";
  const status = (searchParams.get("status") ?? "") as IncidentStatus | "";
  const severity = (searchParams.get("severity") ?? "") as Severity | "";
  const dateFrom = searchParams.get("date_from") ?? "";
  const dateTo = searchParams.get("date_to") ?? "";

  function setParam(key: string, value: string) {
    setSearchParams(
      (prev) => {
        const next = new URLSearchParams(prev);
        if (value) next.set(key, value);
        else next.delete(key);
        return next;
      },
      { replace: true },
    );
  }

  const filters = {
    equipment_id: equipmentId || undefined,
    search: search || undefined,
    status: status || undefined,
    severity: severity || undefined,
    date_from: dateFrom || undefined,
    date_to: dateTo ? dateTo + "T23:59:59Z" : undefined,
    page_size: PAGE_SIZE,
    sort_by: "created_at",
    sort_order: "desc" as const,
  };

  const {
    data,
    isLoading,
    isFetchingNextPage,
    fetchNextPage,
    hasNextPage,
  } = useInfiniteQuery({
    queryKey: ["incident-history", filters],
    queryFn: ({ pageParam = 1 }) =>
      getIncidents({ ...filters, page: pageParam as number }),
    initialPageParam: 1,
    getNextPageParam: (lastPage) => {
      const fetched = (lastPage.page - 1) * lastPage.page_size + lastPage.items.length;
      return fetched < lastPage.total ? lastPage.page + 1 : undefined;
    },
  });

  const incidents = data?.pages.flatMap((p) => p.items) ?? [];
  const total = data?.pages[0]?.total ?? 0;

  // Measure sticky bar height → CSS variable for th positioning
  const stickyBarRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const el = stickyBarRef.current;
    if (!el) return;
    const ro = new ResizeObserver(() => {
      document.documentElement.style.setProperty(
        "--filter-bar-height",
        `${el.offsetHeight}px`,
      );
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  // Infinite scroll sentinel
  const sentinelRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const el = sentinelRef.current;
    if (!el) return;
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting && hasNextPage && !isFetchingNextPage) {
          fetchNextPage();
        }
      },
      { threshold: 0.1 },
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, [fetchNextPage, hasNextPage, isFetchingNextPage]);

  return (
    <div className="page-history">
      <Breadcrumb items={[{ label: "Operations Dashboard", to: "/" }, { label: "History & Audit" }]} />
      <h1 className="page-title">Incident History & Audit</h1>

      <div className="history-sticky-bar" ref={stickyBarRef}>
        <Filters
          search={search}
          onSearchChange={(v) => setParam("search", v)}
          status={status}
          onStatusChange={(v) => setParam("status", v)}
          severity={severity}
          onSeverityChange={(v) => setParam("severity", v)}
          dateFrom={dateFrom}
          onDateFromChange={(v) => setParam("date_from", v)}
          dateTo={dateTo}
          onDateToChange={(v) => setParam("date_to", v)}
        />
        <div className="history-meta">
          <span>
            Showing {incidents.length} of {total} incidents{equipmentId ? ` for ${equipmentId}` : ""}
          </span>
          <div className="history-meta-actions">
            {equipmentId && (
              <button
                className="btn btn--secondary btn--sm"
                onClick={() => setParam("equipment_id", "")}
              >
                Clear equipment filter
              </button>
            )}
            <button
              className="btn btn--secondary btn--sm"
              onClick={() => exportIncidentsToCSV(incidents)}
              disabled={incidents.length === 0}
              title={`Export ${incidents.length} loaded incident${incidents.length !== 1 ? "s" : ""} to CSV`}
            >
              ↓ Export CSV
            </button>
          </div>
        </div>
      </div>

      {isLoading ? (
        <div className="loading">Loading...</div>
      ) : (
        <>
          <IncidentTable incidents={incidents} />
          <div ref={sentinelRef} style={{ height: 1 }} />
          {isFetchingNextPage && (
            <div className="pagination-loading">Loading more…</div>
          )}
          {!hasNextPage && incidents.length > 0 && (
            <div className="pagination-end">All {total} incidents loaded</div>
          )}
        </>
      )}
    </div>
  );
}
