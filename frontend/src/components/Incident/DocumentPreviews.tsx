import type { DocumentDraft } from "../../types/incident";

interface Props {
  drafts: DocumentDraft[];
}

export default function DocumentPreviews({ drafts }: Props) {
  if (drafts.length === 0) return null;
  return (
    <section className="incident-section">
      <h3 className="section-title">Documents</h3>
      {drafts.map((doc, i) => (
        <div key={i} className="doc-preview">
          <span className="doc-icon">📝</span>
          <span className="doc-title">{doc.title}</span>
          <span className="doc-type badge badge--closed">
            {doc.type === "work_order" ? "Work Order" : "Audit Entry"} Draft
          </span>
        </div>
      ))}
    </section>
  );
}
