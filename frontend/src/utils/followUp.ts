import type { Incident, IncidentEvent, IncidentStatus } from "../types/incident";

const FOLLOW_UP_PROCESSING_STATUSES = new Set<IncidentStatus>([
  "awaiting_agents",
  "queued_for_analysis",
  "analyzing",
]);

const FOLLOW_UP_PROCESSING_STEPS = new Set([
  "queued_for_analysis_followup",
  "analyzing_followup",
]);

export interface FollowUpRequest {
  question?: string;
  requestedAt?: string;
}

export interface PendingFollowUpState extends FollowUpRequest {
  isPending: boolean;
}

export function getPendingFollowUpState(
  incident: Incident,
  events: IncidentEvent[],
): PendingFollowUpState {
  const request = getLatestFollowUpRequest(incident, events);

  if (!request || !isIncidentFollowUpProcessing(incident)) {
    return { isPending: false };
  }

  const requestTime = parseEventTime(request.requestedAt);
  const hasResponseAfterRequest = requestTime !== undefined && events.some((event) => {
    if (event.action !== "agent_response") return false;
    const responseTime = parseEventTime(event.timestamp);
    return responseTime !== undefined && responseTime > requestTime;
  });

  return {
    ...request,
    isPending: !hasResponseAfterRequest,
  };
}

export function getLatestFollowUpRequest(
  incident: Incident,
  events: IncidentEvent[],
): FollowUpRequest | undefined {
  const latestRequestEvent = getLatestFollowUpRequestEvent(events);
  const fallbackQuestion = incident.lastDecision?.action === "more_info"
    ? incident.lastDecision.question?.trim()
    : undefined;

  if (latestRequestEvent) {
    return {
      question: latestRequestEvent.details.trim() || fallbackQuestion,
      requestedAt: latestRequestEvent.timestamp,
    };
  }

  return fallbackQuestion ? { question: fallbackQuestion } : undefined;
}

export function isIncidentFollowUpProcessing(incident: Incident) {
  if (FOLLOW_UP_PROCESSING_STATUSES.has(incident.status)) return true;

  const currentStep = String(incident.workflow_state?.current_step || "")
    .trim()
    .toLowerCase();
  return FOLLOW_UP_PROCESSING_STEPS.has(currentStep);
}

function getLatestFollowUpRequestEvent(events: IncidentEvent[]) {
  return events
    .filter((event) => event.action === "more_info" || event.action === "operator_question")
    .sort((left, right) => getSortableTime(right.timestamp) - getSortableTime(left.timestamp))[0];
}

function getSortableTime(timestamp?: string) {
  return parseEventTime(timestamp) ?? Number.NEGATIVE_INFINITY;
}

function parseEventTime(timestamp?: string) {
  if (!timestamp) return undefined;

  const parsed = Date.parse(timestamp);
  return Number.isNaN(parsed) ? undefined : parsed;
}
