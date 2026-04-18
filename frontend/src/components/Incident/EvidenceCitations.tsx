import type { EvidenceCitation as Citation } from "../../types/incident";

const ICON_MAP: Record<string, string> = {
  sop: "📄",
  historical: "📋",
  gmp: "📖",
  bpr: "📑",
};

interface Props {
  citations: Citation[];
}

export default function EvidenceCitations({ citations }: Props) {
  if (!Array.isArray(citations) || citations.length === 0) return null;
  return (
    <section className="incident-section">
      <h3 className="section-title">Evidence Citations</h3>
      <ul className="evidence-list">
        {citations.map((c, i) => (
          <li key={i} className="evidence-item">
            <span className="evidence-icon">{ICON_MAP[c.type] ?? "📄"}</span>
            <span className="evidence-ref">
              {c.reference}
              {c.section ? ` §${c.section}` : ""}
            </span>
            <span className="evidence-relevance">{c.relevance}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}
