import {
  useState,
  useEffect,
  useRef,
  useCallback,
  type ChangeEvent,
  type KeyboardEvent,
} from "react";
import { useNavigate } from "react-router-dom";
import { useIncidents } from "../../hooks/useIncidents";
import { useAuth } from "../../hooks/useAuth";

interface CommandItem {
  id: string;
  icon: string;
  label: string;
  description?: string;
  category: string;
  action: () => void;
}

interface Props {
  open: boolean;
  onClose: () => void;
}

export default function CommandPalette({ open, onClose }: Props) {
  const [query, setQuery] = useState("");
  const [activeIdx, setActiveIdx] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const navigate = useNavigate();
  const { roles } = useAuth();

  const { data: activeData } = useIncidents({
    status: ["pending_approval", "escalated", "analyzing", "ingested"],
    page_size: 20,
  });

  const go = useCallback(
    (path: string) => {
      navigate(path);
      onClose();
    },
    [navigate, onClose],
  );

  const NAV_COMMANDS: CommandItem[] = [
    {
      id: "nav-ops",
      icon: "📋",
      label: "Operations Dashboard",
      description: "Active incidents requiring attention",
      category: "Navigate",
      action: () => go("/"),
    },
    {
      id: "nav-history",
      icon: "📂",
      label: "History & Audit",
      description: "Full incident log with filters",
      category: "Navigate",
      action: () => go("/history"),
    },
    ...(roles.includes("qa-manager") || roles.includes("it-admin")
      ? [
          {
            id: "nav-manager",
            icon: "📊",
            label: "Manager Dashboard",
            description: "KPIs, escalations, recent decisions",
            category: "Navigate",
            action: () => go("/manager"),
          },
        ]
      : []),
    ...(roles.includes("qa-manager") || roles.includes("it-admin") || roles.includes("auditor")
      ? [
          {
            id: "nav-telemetry",
            icon: "🧭",
            label: "Incident Telemetry",
            description: "Backend-visible Foundry trace by incident",
            category: "Navigate",
            action: () => go("/telemetry"),
          },
        ]
      : []),
    ...(roles.includes("it-admin")
      ? [
          {
            id: "nav-templates",
            icon: "📄",
            label: "Document Templates",
            description: "Manage CAPA & report templates",
            category: "Navigate",
            action: () => go("/templates"),
          },
        ]
      : []),
  ];

  const incidentCommands: CommandItem[] = (activeData?.items ?? []).map(
    (inc) => ({
      id: `inc-${inc.id}`,
      icon: inc.status === "escalated" ? "🔴" : inc.status === "pending_approval" ? "🟡" : "🔵",
      label: inc.incident_number ?? inc.id,
      description: inc.title ?? `${inc.equipment_id} · ${inc.status.replace(/_/g, " ")}`,
      category: "Active Incidents",
      action: () => go(`/incidents/${inc.id}`),
    }),
  );

  const allCommands = [...NAV_COMMANDS, ...incidentCommands];

  const filtered = query.trim()
    ? allCommands.filter(
        (c) =>
          c.label.toLowerCase().includes(query.toLowerCase()) ||
          (c.description ?? "").toLowerCase().includes(query.toLowerCase()),
      )
    : allCommands;

  // Group results
  const groups = filtered.reduce<Record<string, CommandItem[]>>((acc, item) => {
    if (!acc[item.category]) acc[item.category] = [];
    acc[item.category].push(item);
    return acc;
  }, {});

  // Flat list for keyboard nav
  const flat = Object.values(groups).flat();

  useEffect(() => {
    if (open) {
      const timer = setTimeout(() => inputRef.current?.focus(), 10);
      return () => clearTimeout(timer);
    }
  }, [open]);

  const handleQueryChange = (e: ChangeEvent<HTMLInputElement>) => {
    setQuery(e.target.value);
    setActiveIdx(0);
  };

  const handleKey = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActiveIdx((i) => Math.min(i + 1, flat.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActiveIdx((i) => Math.max(i - 1, 0));
    } else if (e.key === "Enter") {
      e.preventDefault();
      flat[activeIdx]?.action();
    } else if (e.key === "Escape") {
      onClose();
    }
  };

  if (!open) return null;

  let flatIdx = 0;

  return (
    <div className="cp-overlay" onClick={onClose}>
      <div className="cp-modal" onClick={(e) => e.stopPropagation()}>
        <div className="cp-search-row">
          <span className="cp-search-icon">⌘</span>
          <input
            ref={inputRef}
            className="cp-input"
            placeholder="Search pages, incidents…"
            value={query}
            onChange={handleQueryChange}
            onKeyDown={handleKey}
            autoComplete="off"
            spellCheck={false}
          />
          <kbd className="cp-esc-hint">Esc</kbd>
        </div>

        <div className="cp-results">
          {flat.length === 0 && (
            <div className="cp-empty">No results for "{query}"</div>
          )}
          {Object.entries(groups).map(([category, items]) => (
            <div key={category} className="cp-group">
              <div className="cp-group-label">{category}</div>
              {items.map((item) => {
                const idx = flatIdx++;
                const isActive = idx === activeIdx;
                return (
                  <button
                    key={item.id}
                    className={`cp-item ${isActive ? "cp-item--active" : ""}`}
                    onClick={item.action}
                    onMouseEnter={() => setActiveIdx(idx)}
                  >
                    <span className="cp-item-icon">{item.icon}</span>
                    <span className="cp-item-text">
                      <span className="cp-item-label">{item.label}</span>
                      {item.description && (
                        <span className="cp-item-desc">{item.description}</span>
                      )}
                    </span>
                  </button>
                );
              })}
            </div>
          ))}
        </div>

        <div className="cp-footer">
          <span><kbd>↑↓</kbd> navigate</span>
          <span><kbd>↵</kbd> open</span>
          <span><kbd>Esc</kbd> close</span>
        </div>
      </div>
    </div>
  );
}
