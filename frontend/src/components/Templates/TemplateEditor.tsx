import { useState } from "react";
import type { Template } from "../../types/template";

interface Props {
  template: Template;
  onSave: (updated: Partial<Template>) => void;
  onCancel: () => void;
}

export default function TemplateEditor({ template, onSave, onCancel }: Props) {
  const [name, setName] = useState(template.name);
  const [descriptionTemplate, setDescriptionTemplate] = useState(
    template.description_template,
  );
  const [priority, setPriority] = useState(template.default_priority ?? "");
  const [team, setTeam] = useState(template.assigned_team ?? "");

  const handleSave = () => {
    onSave({
      name,
      description_template: descriptionTemplate,
      default_priority: priority || undefined,
      assigned_team: team || undefined,
    });
  };

  return (
    <div className="template-editor">
      <h3>{template.name} — v{template.version}</h3>

      <label className="form-label">
        Template Name
        <input
          className="form-input"
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
      </label>

      <label className="form-label">
        Default Priority
        <select
          className="filter-select"
          value={priority}
          onChange={(e) => setPriority(e.target.value)}
        >
          <option value="">None</option>
          <option value="Low">Low</option>
          <option value="Medium">Medium</option>
          <option value="High">High</option>
          <option value="Critical">Critical</option>
        </select>
      </label>

      <label className="form-label">
        Assigned Team
        <input
          className="form-input"
          value={team}
          onChange={(e) => setTeam(e.target.value)}
        />
      </label>

      <label className="form-label">
        Description Template
        <textarea
          className="form-textarea"
          rows={8}
          value={descriptionTemplate}
          onChange={(e) => setDescriptionTemplate(e.target.value)}
        />
      </label>

      <div className="form-actions">
        <button className="btn btn--secondary" onClick={onCancel}>
          Cancel
        </button>
        <button className="btn btn--primary" onClick={handleSave}>
          💾 Save
        </button>
      </div>
    </div>
  );
}
