import { type ChangeEvent } from "react";
import type { Incident } from "../../types/incident";
import type { AuditEntryDraft, WorkOrderDraft } from "../../types/approval";
import {
  getAllCitations,
  getCapaActions,
  getClassification,
  getConfidencePct,
  getParameterSummary,
  getRecommendation,
  getRootCause,
  labelize,
} from "../../utils/analysis";
import EvidenceCitations from "./EvidenceCitations";
import AgentRecommendationBadge from "../Approval/AgentRecommendationBadge";

interface DraftState {
  workOrder: WorkOrderDraft;
  auditEntry: AuditEntryDraft;
}

interface Props {
  incident: Incident;
  /** Present only when the incident is pending and the user can edit */
  editableDrafts?: DraftState;
  onDraftChange?: (drafts: DraftState) => void;
  isAwaitingFollowUp?: boolean;
}

export default function DecisionPackage({
  incident,
  editableDrafts,
  onDraftChange,
  isAwaitingFollowUp = false,
}: Props) {
  const analysis = incident.ai_analysis;
  const parameter = getParameterSummary(incident);
  const citations = getAllCitations(analysis);
  const capaActions = getCapaActions(analysis);
  const isEditable = !!editableDrafts && !!onDraftChange;

  function handleWoChange(e: ChangeEvent<HTMLTextAreaElement | HTMLInputElement>) {
    if (!editableDrafts || !onDraftChange) return;
    onDraftChange({
      ...editableDrafts,
      workOrder: { ...editableDrafts.workOrder, [e.target.name]: e.target.value },
    });
  }

  function handleAeChange(e: ChangeEvent<HTMLTextAreaElement | HTMLInputElement>) {
    if (!editableDrafts || !onDraftChange) return;
    onDraftChange({
      ...editableDrafts,
      auditEntry: { ...editableDrafts.auditEntry, [e.target.name]: e.target.value },
    });
  }

  return (
    <section className="decision-package">
      <h2 className="decision-package-title">Decision Package</h2>

      <div className="decision-summary-strip">
        <div className="decision-summary-strip-header">
          <h3 className="section-title">Incident Summary</h3>
          <span className="decision-summary-strip-text">
            What happened and where it affects the batch.
          </span>
        </div>
        <div className="decision-metric-grid">
          <Metric label="Equipment" value={incident.equipment_id} />
          <Metric label="Batch" value={incident.batch_id} />
          <Metric label="Product" value={incident.product} />
          <Metric label="Stage" value={incident.production_stage} />
          <Metric label="Parameter" value={parameter.parameter} />
          <Metric
            label="Measured"
            value={
              parameter.measuredValue !== undefined
                ? `${parameter.measuredValue} ${parameter.unit}`
                : undefined
            }
          />
          <Metric
            label="Limit"
            value={
              parameter.lowerLimit !== undefined && parameter.upperLimit !== undefined
                ? `${parameter.lowerLimit}-${parameter.upperLimit} ${parameter.unit}`
                : undefined
            }
          />
          <Metric
            label="Duration"
            value={
              parameter.durationSeconds !== undefined
                ? `${Math.floor(parameter.durationSeconds / 60)}m ${parameter.durationSeconds % 60}s`
                : undefined
            }
          />
          <Metric label="Severity" value={incident.severity} />
          <Metric label="Status" value={incident.status} />
        </div>
      </div>

      {isAwaitingFollowUp && (
        <div className="decision-followup-notice" role="status">
          <strong>Follow-up in progress</strong>
          <span>The recommendation below is the previous agent answer until the updated response arrives.</span>
        </div>
      )}

      {analysis && (
        <div className={`decision-section decision-section--primary${isAwaitingFollowUp ? " decision-section--stale" : ""}`}>
          <h3 className="section-title">
            {isAwaitingFollowUp ? "Previous AI Recommendation" : "AI Recommendation for this Incident"}
          </h3>
          {analysis.agent_recommendation && (
            <AgentRecommendationBadge
              recommendation={analysis.agent_recommendation}
              rationale={analysis.agent_recommendation_rationale ?? analysis.recommendation}
            />
          )}
          <div className="decision-summary-grid">
            <Metric label="Risk" value={analysis.risk_level} />
            <Metric label="Confidence" value={`${getConfidencePct(analysis)}%`} />
            <Metric label="Classification" value={getClassification(analysis)} />
            <Metric label="Batch disposition" value={analysis.batch_disposition} />
          </div>
          {getRecommendation(analysis) && (
            <div className="decision-text-block decision-text-block--highlight">
              <strong>Recommended action</strong>
              <p>{getRecommendation(analysis)}</p>
            </div>
          )}
          {getRootCause(analysis) && (
            <div className="decision-text-block">
              <strong>Root cause</strong>
              <p>{getRootCause(analysis)}</p>
            </div>
          )}
        </div>
      )}

      {citations.length > 0 && (
        <div className="decision-section decision-section--supporting">
          <EvidenceCitations citations={citations} />
        </div>
      )}

      {analysis && (
        <div className="decision-section decision-section--supporting">
          <h3 className="section-title">After Approval</h3>
          {capaActions.length > 0 && (
            <div className="approval-outcome-block">
              <strong>CAPA actions</strong>
              <ol className="capa-list">
                {capaActions.map((action, i) => (
                  <li key={i}>{action}</li>
                ))}
              </ol>
            </div>
          )}

          {isEditable ? (
            <>
              <WorkOrderForm
                draft={editableDrafts.workOrder}
                onChange={handleWoChange}
              />
              <AuditEntryForm
                draft={editableDrafts.auditEntry}
                onChange={handleAeChange}
              />
            </>
          ) : (
            <>
              <DraftBlock
                title={incident.operatorWorkOrderDraft ? "Work order" : "Work order draft"}
                draft={incident.operatorWorkOrderDraft ?? analysis.work_order_draft}
                confirmed={!!incident.operatorWorkOrderDraft}
              />
              {incident.operatorWorkOrderDraft && analysis.work_order_draft &&
                !draftsAreIdentical(incident.operatorWorkOrderDraft, analysis.work_order_draft as Record<string, unknown>) && (
                <DraftBlock
                  title="Work order (AI original)"
                  draft={analysis.work_order_draft as Record<string, unknown>}
                  aiDraft
                />
              )}
              <DraftBlock
                title={incident.operatorAuditEntryDraft ? "Audit entry" : "Audit entry draft"}
                draft={incident.operatorAuditEntryDraft ?? analysis.audit_entry_draft}
                confirmed={!!incident.operatorAuditEntryDraft}
              />
              {incident.operatorAuditEntryDraft && analysis.audit_entry_draft &&
                !draftsAreIdentical(incident.operatorAuditEntryDraft, analysis.audit_entry_draft as Record<string, unknown>) && (
                <DraftBlock
                  title="Audit entry (AI original)"
                  draft={analysis.audit_entry_draft as Record<string, unknown>}
                  aiDraft
                />
              )}
            </>
          )}
        </div>
      )}
    </section>
  );
}

function Metric({ label, value }: { label: string; value?: string | number }) {
  return (
    <div className="decision-metric">
      <span>{label}</span>
      <strong>{labelize(value)}</strong>
    </div>
  );
}

/** Returns true if every key in `operator` has the same string value in `ai`. */
function draftsAreIdentical(
  operator: Record<string, unknown>,
  ai: Record<string, unknown>,
): boolean {
  return Object.entries(operator).every(([k, v]) => {
    const aiVal = ai[k];
    return String(v ?? "").trim() === String(aiVal ?? "").trim();
  });
}

function DraftBlock({
  title,
  draft,
  confirmed,
  aiDraft,
}: {
  title: string;
  draft?: Record<string, unknown>;
  confirmed?: boolean;
  aiDraft?: boolean;
}) {
  if (!draft || Object.keys(draft).length === 0) return null;
  const className = confirmed
    ? "draft-block draft-block--confirmed"
    : aiDraft
    ? "draft-block draft-block--ai-draft"
    : "draft-block";
  return (
    <div className={className}>
      <strong>
        {title}
        {confirmed && <span className="draft-block-confirmed-badge">Operator confirmed</span>}
        {aiDraft && <span className="draft-block-ai-draft-badge">AI draft</span>}
      </strong>
      <dl className="draft-grid">
        {Object.entries(draft).map(([key, value]) => (
          <div key={key}>
            <dt>{labelize(key)}</dt>
            <dd>{typeof value === "object" ? JSON.stringify(value) : labelize(String(value))}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}

type FieldChangeHandler = (e: ChangeEvent<HTMLTextAreaElement | HTMLInputElement>) => void;

function WorkOrderForm({ draft, onChange }: { draft: WorkOrderDraft; onChange: FieldChangeHandler }) {
  const isBlocked = !draft.title && !draft.description;
  return (
    <div className="draft-form">
      <strong className="draft-form-title">
        Work order draft
        {isBlocked && <span className="draft-form-required">Required</span>}
      </strong>
      <label className="draft-form-field">
        <span>Title</span>
        <input
          type="text"
          name="title"
          value={draft.title ?? ""}
          onChange={onChange}
          placeholder={isBlocked ? "Introduce work order title manually (AI was unable to generate)" : ""}
          className="draft-input"
        />
      </label>
      <label className="draft-form-field">
        <span>Description</span>
        <textarea
          name="description"
          value={draft.description ?? ""}
          onChange={onChange}
          rows={3}
          placeholder={isBlocked ? "Introduce work order description manually (AI was unable to generate)" : ""}
          className="draft-textarea"
        />
      </label>
      <label className="draft-form-field">
        <span>Priority</span>
        <input
          type="text"
          name="priority"
          value={draft.priority ?? ""}
          onChange={onChange}
          placeholder="e.g. urgent, high, normal"
          className="draft-input"
        />
      </label>
    </div>
  );
}

function AuditEntryForm({ draft, onChange }: { draft: AuditEntryDraft; onChange: FieldChangeHandler }) {
  const isBlocked = !draft.description;
  return (
    <div className="draft-form">
      <strong className="draft-form-title">
        Audit entry draft
        {isBlocked && <span className="draft-form-required">Required</span>}
      </strong>
      <label className="draft-form-field">
        <span>Deviation type</span>
        <input
          type="text"
          name="deviation_type"
          value={draft.deviation_type ?? ""}
          onChange={onChange}
          placeholder="e.g. Equipment, Process, Human"
          className="draft-input"
        />
      </label>
      <label className="draft-form-field">
        <span>GMP clause</span>
        <input
          type="text"
          name="gmp_clause"
          value={draft.gmp_clause ?? ""}
          onChange={onChange}
          placeholder="e.g. 21 CFR 211.68"
          className="draft-input"
        />
      </label>
      <label className="draft-form-field">
        <span>Description</span>
        <textarea
          name="description"
          value={draft.description ?? ""}
          onChange={onChange}
          rows={3}
          placeholder={isBlocked ? "Introduce audit entry description manually (AI was unable to generate)" : ""}
          className="draft-textarea"
        />
      </label>
    </div>
  );
}
