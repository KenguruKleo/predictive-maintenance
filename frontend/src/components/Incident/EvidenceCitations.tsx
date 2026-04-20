import type { EvidenceCitation as Citation } from "../../types/incident";
import {
  getCitationHref,
  getCitationLinkLabel,
  getCitationSection,
  getCitationText,
  getCitationTitle,
  isCitationResolved,
  labelize,
} from "../../utils/analysis";

const TYPE_LABELS: Record<string, string> = {
  sop: "SOP",
  historical: "Similar incident",
  gmp: "GMP",
  bpr: "BPR",
  manual: "Manual",
  incident: "Incident",
};

interface Props {
  citations: Citation[];
}

export default function EvidenceCitations({ citations }: Props) {
  if (!Array.isArray(citations) || citations.length === 0) return null;
  return (
    <section>
      <h3 className="section-title">Evidence From Documents</h3>
      <ul className="evidence-list">
        {citations.map((c, i) => {
          const title = getCitationTitle(c);
          const section = getCitationSection(c);
          const text = getCitationText(c);
          const href = getCitationHref(c);
          const linkLabel = getCitationLinkLabel(c);
          const resolved = isCitationResolved(c);
          const typeLabel = TYPE_LABELS[c.type ?? ""] ?? labelize(c.type || c.source || "document");
          return (
            <li key={i} className="evidence-item evidence-card">
              <span className="evidence-icon">{TYPE_LABELS[c.type ?? ""] ?? "Doc"}</span>
              <div className="evidence-body">
                <div className="evidence-ref">
                  {title}
                  {section ? ` ${section}` : ""}
                </div>
                <div className="evidence-meta">
                  {resolved ? typeLabel : "Unresolved evidence"}
                  {typeof c.score === "number" ? ` | score ${c.score.toFixed(2)}` : ""}
                  {c.source_blob ? ` | ${c.source_blob}` : ""}
                  {c.unresolved_reason ? ` | ${c.unresolved_reason}` : ""}
                </div>
                {text && <blockquote className="evidence-quote">{text}</blockquote>}
                {href && (
                  <a
                    className="evidence-open-link"
                    href={href}
                    target="_blank"
                    rel="noreferrer"
                  >
                    {linkLabel}
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
