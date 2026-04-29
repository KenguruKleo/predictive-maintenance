import type { RefObject } from "react";
import type { IncidentEvent } from "../../types/incident";

interface ChatMsg {
  id: string;
  timestamp: string;
  actor: string;
  actor_type: "human" | "agent";
  content: string;
  round?: number | null;
  message_kind?: string;
}

interface Props {
  events: IncidentEvent[];
  onSend?: (message: string) => void;
  draftMessage?: string;
  onDraftChange?: (message: string) => void;
  errorMessage?: string | null;
  readOnly?: boolean;
  showComposer?: boolean;
  title?: string;
  emptyState?: string;
  inputId?: string;
  inputRef?: RefObject<HTMLTextAreaElement | null>;
}

function sortNewestFirst<T extends { timestamp: string }>(items: T[]): T[] {
  return [...items].sort((left, right) => {
    const leftTs = Date.parse(left.timestamp);
    const rightTs = Date.parse(right.timestamp);
    if (Number.isNaN(leftTs) || Number.isNaN(rightTs)) {
      return right.timestamp.localeCompare(left.timestamp);
    }
    return rightTs - leftTs;
  });
}

export default function AgentChat({
  events,
  onSend,
  draftMessage = "",
  onDraftChange,
  errorMessage = null,
  readOnly,
  showComposer = false,
  title = "Agent Conversation",
  emptyState = "Ask the AI agent for more details before deciding.",
  inputId,
  inputRef,
}: Props) {
  const chatMessages: ChatMsg[] = sortNewestFirst(events)
    .filter(
      (e) =>
        e.action === "operator_question" ||
        e.action === "agent_response" ||
        e.action === "more_info",
    )
    .map((e) => ({
      id: e.id,
      timestamp: e.timestamp,
      actor: e.actor,
      actor_type: e.actor_type as "human" | "agent",
      content: e.details,
      round: e.round,
      message_kind: e.message_kind,
    }));

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const form = e.currentTarget;
    const input = form.elements.namedItem("chatInput") as HTMLTextAreaElement;
    const val = input.value.trim();
    if (!val || !onSend) return;
    onSend(val);
  };

  return (
    <div className="agent-chat">
      <h4 className="chat-title">{title}</h4>

      {!readOnly && onSend && showComposer && (
        <form className="chat-input-form" onSubmit={handleSubmit}>
          <textarea
            id={inputId}
            ref={inputRef}
            name="chatInput"
            className="chat-input"
            placeholder="Ask a detailed question..."
            autoComplete="off"
            rows={4}
            value={draftMessage}
            onChange={(event) => onDraftChange?.(event.target.value)}
          />
          {errorMessage && (
            <p className="chat-input-error" role="alert">
              {errorMessage}
            </p>
          )}
          <button type="submit" className="btn btn--primary chat-send">
            Send question
          </button>
        </form>
      )}

      <div className="chat-messages">
        {chatMessages.length === 0 && (
          <div className="chat-empty">
            {emptyState}
          </div>
        )}
        {chatMessages.map((msg) => (
          <div
            key={msg.id}
            className={`chat-bubble chat-bubble--${msg.actor_type}`}
          >
            <span className="chat-sender">
              {msg.actor_type === "human" ? "You" : "Agent"}
              {getMessageLabel(msg) ? ` · ${getMessageLabel(msg)}` : ""} (
              {formatChatTime(msg.timestamp)})
            </span>
            <p className="chat-text">{msg.content}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

function formatChatTime(timestamp: string) {
  const value = new Date(timestamp);
  return Number.isNaN(value.getTime())
    ? timestamp
    : value.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function getMessageLabel(message: ChatMsg) {
  if (message.actor_type === "human") {
    return "Question";
  }

  if (message.message_kind === "initial_recommendation") {
    return "Recommendation";
  }

  if (message.message_kind === "follow_up_response") {
    return message.round ? `Follow-up ${message.round}` : "Follow-up";
  }

  return "Response";
}
