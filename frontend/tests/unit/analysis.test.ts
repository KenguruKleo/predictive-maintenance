import { describe, expect, it } from "vitest";
import {
  getAllCitations,
  getCapaActions,
  getCitationHref,
  getCitationTitle,
  getClassification,
  getConfidencePct,
  getDisplayLabel,
  getRecommendation,
  getRootCause,
  labelize,
} from "../../src/utils/analysis";
import type { AiAnalysis } from "../../src/types/incident";

describe("analysis utils", () => {
  it("formats labels and falls back to human-readable defaults", () => {
    expect(labelize("pending_approval")).toBe("pending approval");
    expect(labelize(null)).toBe("Not provided");
    expect(getDisplayLabel("pending_approval")).toBe("Pending Approval");
    expect(getDisplayLabel(null)).toBe("Not provided");
  });

  it("extracts analysis fields with compatibility fallbacks", () => {
    const analysis: AiAnalysis = {
      risk_level: "MEDIUM",
      confidence: 0.82,
      deviation_classification: "process deviation",
      root_cause_hypothesis: "sensor drift",
      analysis: "Short transient excursion.",
      evidence_citations: [],
    };

    expect(getClassification(analysis)).toBe("process deviation");
    expect(getRootCause(analysis)).toBe("sensor drift");
    expect(getRecommendation(analysis)).toBe("Short transient excursion.");
    expect(getConfidencePct(analysis)).toBe(82);
    expect(getConfidencePct({ ...analysis, confidence: 82 })).toBe(82);
  });

  it("builds CAPA action strings from structured recommendations or suggestion text", () => {
    expect(getCapaActions({
      risk_level: "HIGH",
      confidence: 0.9,
      evidence_citations: [],
      recommendations: [
        {
          action: "Inspect granulator",
          owner: "Maintenance",
          priority: "high",
          deadline_days: 2,
        },
      ],
    })).toEqual(["Inspect granulator | Owner: Maintenance | Priority: high | Due: 2d"]);

    expect(getCapaActions({
      risk_level: "LOW",
      confidence: 0.5,
      evidence_citations: [],
      capa_suggestion: "1. Review logs\n2. Confirm line settings",
    })).toEqual(["Review logs", "Confirm line settings"]);
  });

  it("filters duplicate and incident citations while keeping known document links resolvable", () => {
    const analysis: AiAnalysis = {
      risk_level: "LOW",
      confidence: 0.4,
      evidence_citations: [
        {
          type: "incident",
          document_id: "INC-2026-0001",
          text_excerpt: "Historical incident",
        },
        {
          type: "sop",
          document_id: "SOP-DEV-001",
          document_title: "Deviation Management",
          text_excerpt: "SOP-DEV-001 requires documented assessment.",
          resolution_status: "resolved",
        },
        {
          type: "sop",
          document_id: "SOP-DEV-001",
          document_title: "Deviation Management",
          text_excerpt: "SOP-DEV-001 requires documented assessment.",
          resolution_status: "resolved",
        },
      ],
    };

    const citations = getAllCitations(analysis);

    expect(citations).toHaveLength(1);
    expect(getCitationTitle(citations[0])).toBe("Deviation Management (SOP-DEV-001)");
    expect(getCitationHref(citations[0])).toContain(
      "/documents/blob-sop/SOP-DEV-001-Deviation-Management.md",
    );
  });
});