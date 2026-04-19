import { API_BASE_URL } from "../authConfig";
import type { AiAnalysis, EvidenceCitation, Incident } from "../types/incident";

export function labelize(value?: string | number | null): string {
  if (value === undefined || value === null || value === "") return "Not provided";
  return String(value).replace(/_/g, " ");
}

export function getDisplayLabel(value?: string | number | null): string {
  const text = labelize(value);
  return text === "Not provided"
    ? text
    : text.replace(/\b\w/g, (char) => char.toUpperCase());
}

export function getClassification(analysis?: AiAnalysis): string {
  return analysis?.classification || analysis?.deviation_classification || "";
}

export function getRootCause(analysis?: AiAnalysis): string {
  return analysis?.root_cause || analysis?.root_cause_hypothesis || "";
}

export function getRecommendation(analysis?: AiAnalysis): string {
  return analysis?.recommendation || analysis?.analysis || "";
}

export function getConfidencePct(analysis?: AiAnalysis): number {
  const confidence = analysis?.confidence ?? 0;
  return Math.round(confidence * (confidence <= 1 ? 100 : 1));
}

export function getCapaActions(analysis?: AiAnalysis): string[] {
  if (!analysis) return [];
  if (Array.isArray(analysis.recommendations) && analysis.recommendations.length > 0) {
    return analysis.recommendations.map((r) => {
      const bits = [
        r.action,
        r.owner ? `Owner: ${r.owner}` : "",
        r.priority ? `Priority: ${r.priority}` : "",
        typeof r.deadline_days === "number" ? `Due: ${r.deadline_days}d` : "",
      ].filter(Boolean);
      return bits.join(" | ");
    });
  }
  if (Array.isArray(analysis.capa_steps) && analysis.capa_steps.length > 0) {
    return analysis.capa_steps.map((step) => step.description);
  }
  if (analysis.capa_suggestion) {
    return analysis.capa_suggestion
      .split(/\n|\d+\.\s/)
      .map((s) => s.trim())
      .filter(Boolean);
  }
  return [];
}

export function getAllCitations(analysis?: AiAnalysis): EvidenceCitation[] {
  if (!analysis) return [];
  const citations = analysis.evidence_citations ?? [];

  const seen = new Set<string>();
  return citations.filter((c) => {
    const primaryId =
      c.document_id || c.source_blob || c.url || c.reference || c.source || c.document_title || "";
    const key = [
      c.type,
      primaryId,
      getCitationSection(c),
      c.resolution_status,
    ].join("|");
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

export function getCitationTitle(citation: EvidenceCitation): string {
  if (citation.resolution_status === "unresolved") {
    return "Unresolved evidence";
  }
  const known = inferKnownDocument(citation);
  if (known?.title) {
    return known.title;
  }
  return (
    citation.document_title ||
    citation.reference ||
    citation.source ||
    citation.document_id ||
    "Document evidence"
  );
}

export function getCitationSection(citation: EvidenceCitation): string {
  return citation.section || citation.relevant_section || "";
}

export function getCitationText(citation: EvidenceCitation): string {
  return citation.text_excerpt || citation.unresolved_reason || citation.relevance || "";
}

export function getCitationHref(citation: EvidenceCitation): string {
  if (citation.resolution_status === "unresolved") {
    return "";
  }
  if (citation.url) {
    if (citation.url.startsWith("http")) return citation.url;
    if (citation.url.startsWith("/api/")) {
      return `${API_BASE_URL.replace(/\/api\/?$/, "")}${citation.url}`;
    }
    return citation.url;
  }
  if (citation.container && citation.source_blob) {
    return `${API_BASE_URL}/documents/${encodeURIComponent(citation.container)}/${encodeURI(citation.source_blob)}`;
  }
  const known = inferKnownDocument(citation);
  if (known) {
    return `${API_BASE_URL}/documents/${known.container}/${encodeURI(known.sourceBlob)}`;
  }
  return "";
}

export function getCitationLinkLabel(citation: EvidenceCitation): string {
  return citation.type === "historical" ? "Open incident" : "Open document";
}

export function isCitationResolved(citation: EvidenceCitation): boolean {
  return citation.resolution_status !== "unresolved";
}

export function getParameterSummary(incident: Incident) {
  const excursion = incident.parameter_excursion;
  return {
    parameter: excursion?.parameter || incident.parameter || "Not provided",
    measuredValue: excursion?.measured_value ?? incident.measured_value,
    lowerLimit: excursion?.lower_limit ?? excursion?.nor_min ?? incident.lower_limit,
    upperLimit: excursion?.upper_limit ?? excursion?.nor_max ?? incident.upper_limit,
    unit: excursion?.unit || incident.unit || "",
    durationSeconds: excursion?.duration_seconds ?? incident.duration_seconds,
  };
}

function inferKnownDocument(citation: EvidenceCitation):
  | { container: string; sourceBlob: string; title: string }
  | undefined {
  const text = [
    citation.document_id,
    citation.document_title,
    citation.reference,
    citation.source,
    citation.text_excerpt,
  ]
    .filter(Boolean)
    .join(" ")
    .toLowerCase();

  if (text.includes("sop-dev-001")) {
    return {
      container: "blob-sop",
      sourceBlob: "SOP-DEV-001-Deviation-Management.md",
      title: "Deviation Management (SOP-DEV-001)",
    };
  }
  if (text.includes("sop-man-gr-001") || text.includes("granulator operation")) {
    return {
      container: "blob-sop",
      sourceBlob: "SOP-MAN-GR-001-Granulator-Operation.md",
      title: "Granulator Operation (SOP-MAN-GR-001)",
    };
  }
  if (text.includes("annex 15") || text.includes("eu gmp")) {
    return {
      container: "blob-gmp",
      sourceBlob: "GMP-Annex15-Excerpt.md",
      title: "EU GMP Annex 15",
    };
  }
  if (text.includes("metformin") || text.includes("b26041701")) {
    return {
      container: "blob-bpr",
      sourceBlob: "BPR-MET-500-v3.2-Process-Specification.md",
      title: "BPR Metformin 500mg Process Specification",
    };
  }
  return undefined;
}
