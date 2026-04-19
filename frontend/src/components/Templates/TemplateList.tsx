import type { Template } from "../../types/template";

interface Props {
  templates: Template[];
  onEdit: (id: string) => void;
}

function formatTemplateFields(fields: Template["fields"]): string {
  if (Array.isArray(fields)) {
    return fields.join(", ");
  }

  return Object.keys(fields ?? {}).join(", ");
}

export default function TemplateList({ templates, onEdit }: Props) {
  return (
    <div className="template-list">
      {templates.map((tpl) => (
        <div key={tpl.id} className="template-card">
          <div className="template-card-header">
            <span className="template-icon">📄</span>
            <span className="template-name">{tpl.name}</span>
            <span className="badge badge--closed">v{tpl.version}</span>
            <button
              className="btn btn--secondary btn--sm"
              onClick={() => onEdit(tpl.id)}
            >
              Edit →
            </button>
          </div>
          <div className="template-meta">
            Type: {tpl.type.replace("_", " ")} · Last modified:{" "}
            {new Date(tpl.last_modified_at).toLocaleDateString()} by{" "}
            {tpl.last_modified_by}
          </div>
          <div className="template-fields">
            Fields: {formatTemplateFields(tpl.fields)}
          </div>
        </div>
      ))}
    </div>
  );
}
