import type { IncidentEvent } from "../../types/incident";

interface ChatMsg {
  timestamp: string;
  actor: string;
  actor_type: "human" | "agent";
  content: string;
}

interface Props {
  events: IncidentEvent[];
  onSend?: (message: string) => void;
  readOnly?: boolean;
}

export default function AgentChat({ events, onSend, readOnly }: Props) {
  const chatMessages: ChatMsg[] = events
    .filter(
      (e) =>
        e.action === "operator_question" || e.action === "agent_response",
    )
    .map((e) => ({
      timestamp: e.timestamp,
      actor: e.actor,
      actor_type: e.actor_type as "human" | "agent",
      content: e.details,
    }));

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const form = e.currentTarget;
    const input = form.elements.namedItem("chatInput") as HTMLInputElement;
    const val = input.value.trim();
    if (!val || !onSend) return;
    onSend(val);
    input.value = "";
  };

  return (
    <div className="agent-chat">
      <h4 className="chat-title">💬 Agent Conversation</h4>
      <div className="chat-messages">
        {chatMessages.length === 0 && (
          <div className="chat-empty">
            Ask the AI agent for more details before deciding.
          </div>
        )}
        {chatMessages.map((msg, i) => (
          <div
            key={i}
            className={`chat-bubble chat-bubble--${msg.actor_type}`}
          >
            <span className="chat-sender">
              {msg.actor_type === "human" ? "👤 You" : "🤖 Agent"} (
              {new Date(msg.timestamp).toLocaleTimeString()})
            </span>
            <p className="chat-text">{msg.content}</p>
          </div>
        ))}
      </div>

      {!readOnly && onSend && (
        <form className="chat-input-form" onSubmit={handleSubmit}>
          <input
            name="chatInput"
            type="text"
            className="chat-input"
            placeholder="Ask a question..."
            autoComplete="off"
          />
          <button type="submit" className="btn btn--primary chat-send">
            ➤
          </button>
        </form>
      )}
    </div>
  );
}
