import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getTemplates, updateTemplate } from "../api/templates";
import TemplateList from "../components/Templates/TemplateList";
import TemplateEditor from "../components/Templates/TemplateEditor";
import type { Template } from "../types/template";

export default function TemplateManagementPage() {
  const [editingId, setEditingId] = useState<string | null>(null);
  const queryClient = useQueryClient();
  const { data: templates = [], isLoading } = useQuery({
    queryKey: ["templates"],
    queryFn: getTemplates,
  });

  const mutation = useMutation({
    mutationFn: (args: { id: string; data: Partial<Template> }) =>
      updateTemplate(args.id, args.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["templates"] });
      setEditingId(null);
    },
  });

  const editingTemplate = templates.find((t) => t.id === editingId);

  if (isLoading) return <div className="loading">Loading templates...</div>;

  return (
    <div className="page-templates">
      <h1 className="page-title">Document Templates</h1>

      {editingTemplate ? (
        <TemplateEditor
          template={editingTemplate}
          onSave={(data) =>
            mutation.mutate({ id: editingTemplate.id, data })
          }
          onCancel={() => setEditingId(null)}
        />
      ) : (
        <TemplateList templates={templates} onEdit={setEditingId} />
      )}
    </div>
  );
}
