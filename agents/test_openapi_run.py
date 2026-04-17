"""Quick test: verify OpenApiTool works server-side (no approval needed)."""
import os, time, sys

os.environ.setdefault("AZURE_AI_AGENTS_TESTS_IS_TEST_RUN", "True")

from azure.ai.agents import AgentsClient
from azure.identity import DefaultAzureCredential

endpoint = os.environ.get("AZURE_AI_FOUNDRY_AGENTS_ENDPOINT", "")
if not endpoint:
    sys.exit("Set AZURE_AI_FOUNDRY_AGENTS_ENDPOINT")

client = AgentsClient(endpoint=endpoint, credential=DefaultAzureCredential())

agent_id = sys.argv[1] if len(sys.argv) > 1 else "asst_NDuVHHTsxfRvY1mRSd7MtEGT"
prompt = sys.argv[2] if len(sys.argv) > 2 else "Get equipment data for GR-204. Return name and criticality only."

thread = client.threads.create()
print(f"Thread: {thread.id}")

client.messages.create(thread_id=thread.id, role="user", content=prompt)
run = client.runs.create(thread_id=thread.id, agent_id=agent_id)
print(f"Run: {run.id} status={run.status}")

for i in range(40):
    time.sleep(2)
    run = client.runs.get(thread_id=thread.id, run_id=run.id)
    status = run.status
    print(f"  [{i*2:>3}s] {status}")
    if status in ("completed", "failed", "cancelled", "expired"):
        break
    if status == "requires_action":
        action = run.required_action
        print(f"  !! requires_action: {action.type if action else '?'}")
        break

if run.status == "completed":
    for m in client.messages.list(thread_id=thread.id):
        if m.role == "assistant":
            for c in m.content:
                if hasattr(c, "text"):
                    print(f"\n{'='*60}\nAssistant:\n{c.text.value}\n{'='*60}")
            break
elif run.status == "failed":
    print(f"\nFAILED: {run.last_error}")
else:
    print(f"\nFinal: {run.status}")
