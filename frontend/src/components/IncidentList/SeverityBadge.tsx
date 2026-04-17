import type { Severity } from "../../types/incident";

const SEVERITY_MAP: Record<Severity, { label: string; className: string }> = {
  critical: { label: "CRITICAL", className: "badge badge--critical" },
  major: { label: "MAJOR", className: "badge badge--major" },
  moderate: { label: "MODERATE", className: "badge badge--moderate" },
  minor: { label: "MINOR", className: "badge badge--minor" },
};

export default function SeverityBadge({ severity }: { severity: Severity }) {
  const cfg = SEVERITY_MAP[severity];
  return <span className={cfg.className}>{cfg.label}</span>;
}
