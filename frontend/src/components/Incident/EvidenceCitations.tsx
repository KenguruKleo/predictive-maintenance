import type { EvidenceCitation as Citation } from "../../types/incident";
import {
  getCitationHref,
  getCitationSection,
  getCitationText,
  getCitationTitle,
  labelize,
} from "../../utils/analysis";

const ICON_MAP: Record<string, string> = {
  sop: "📄",
  historical: "📋",
  gmp: "📖",
  bpr: "📑",
  manual: "🛠️",
  incident: "●",
};

interface Props {
  citations: Citation[];
}

export default function EvidenceCitations({ citations }: Props) {
  if (!Array.isArray(citations) || citations.length === 0) return null;
  return (
    <section className="incident-section">
      <h3 className="section-title">Evidence From Documents</h3>
      <ul className="evidence-list">
        {citations.map((c, i) => {
          const title = getCitationTitle(c);
          const section = getCitationSection(c);
          const text = getCitationText(c);
          const href = getCitationHref(c);
          return (
            <li key={i} className="evidence-item evidence-card">
              <span className="evidence-icon">{ICON_MAP[c.type ?? ""] ?? "📄"}</span>
              <div className="evidence-body">
                <div className="evidence-ref">
                  {title}
                  {section ? ` ${section}` : ""}
                </div>
                <div className="evidence-meta">
                  {labelize(c.type || c.source || "document")}
                  {typeof c.score === "number" ? ` | score ${c.score.toFixed(2)}` : ""}
                  {c.source_blob ? ` | ${c.source_blob}` : ""}
                </div>
                {text && <blockquote className="evidence-quote">{text}</blockquote>}
                {href && (
                  <a
                    className="evidence-open-link"
                    href={href}
                    target="_blank"
                    rel="noreferrer"
                  >
                    Open document
                  </a>
                )}
              </div>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
