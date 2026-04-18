import { useEffect, useRef, useState } from "react";
import { useInfiniteQuery } from "@tanstack/react-query";
import { getIncidents } from "../api/incidents";
import Filters from "../components/IncidentList/Filters";
import Breadcrumb from "../components/Layout/Breadcrumb";
import IncidentTable from "../components/IncidentList/IncidentTable";
import type { IncidentStatus, Severity } from "../types/incident";

const PAGE_SIZE = 20;

export default function IncidentHistoryPage() {
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState<IncidentStatus | "">("");
  const [severity, setSeverity] = useState<Severity | "">("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");

  const filters = {
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
      { threshold: 0.1 }
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, [fetchNextPage, hasNextPage, isFetchingNextPage]);

  return (
    <div className="page-history">
      <Breadcrumb items={[{ label: "Operations Dashboard", to: "/" }, { label: "History & Audit" }]} />
      <h1 className="page-title">Incident History & Audit</h1>

      <Filters
        search={search}
        onSearchChange={setSearch}
        status={status}
        onStatusChange={setStatus}
        severity={severity}
        onSeverityChange={setSeverity}
        dateFrom={dateFrom}
        onDateFromChange={setDateFrom}
        dateTo={dateTo}
        onDateToChange={setDateTo}
      />

      <div className="history-meta">
        Showing {incidents.length} of {total} incidents
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

