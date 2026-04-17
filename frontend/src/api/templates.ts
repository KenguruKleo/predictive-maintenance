import client from "./client";
import type { Template } from "../types/template";

export async function getTemplates(): Promise<Template[]> {
  const { data } = await client.get<Template[]>("/templates");
  return data;
}

export async function updateTemplate(
  id: string,
  template: Partial<Template>,
): Promise<Template> {
  const { data } = await client.put<Template>(
    `/templates/${encodeURIComponent(id)}`,
    template,
  );
  return data;
}
