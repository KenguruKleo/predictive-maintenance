import type { Toast } from "../../hooks/useSignalR";

interface Props {
  toasts: Toast[];
  onDismiss: (id: string) => void;
}

export default function ToastStack({ toasts, onDismiss }: Props) {
  if (!toasts.length) {
    return null;
  }

  return (
    <div className="toast-stack" aria-live="polite" aria-atomic="false">
      {toasts.map((toast) => (
        <div key={toast.id} className={`toast toast--${toast.type}`}>
          <div className="toast-body">
            <div className="toast-label">Live update</div>
            <div className="toast-message">{toast.message}</div>
          </div>
          <button
            type="button"
            className="toast-dismiss"
            aria-label="Dismiss notification"
            onClick={() => onDismiss(toast.id)}
          >
            ×
          </button>
        </div>
      ))}
    </div>
  );
}