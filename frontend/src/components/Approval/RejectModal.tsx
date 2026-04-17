import { useState } from "react";

interface Props {
  onConfirm: (reason: string) => void;
  onCancel: () => void;
}

export default function RejectModal({ onConfirm, onCancel }: Props) {
  const [reason, setReason] = useState("");

  return (
    <div className="modal-overlay" onClick={onCancel}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <h3>Reject Incident</h3>
        <p>Please provide a reason for rejection (required for audit trail).</p>
        <textarea
          className="reject-textarea"
          placeholder="Reason for rejection..."
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          rows={4}
          autoFocus
        />
        <div className="modal-actions">
          <button className="btn btn--secondary" onClick={onCancel}>
            Cancel
          </button>
          <button
            className="btn btn--danger"
            disabled={reason.trim().length < 10}
            onClick={() => onConfirm(reason.trim())}
          >
            Confirm Rejection
          </button>
        </div>
      </div>
    </div>
  );
}
