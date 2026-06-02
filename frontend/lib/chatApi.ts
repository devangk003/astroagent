import { Client } from "@langchain/langgraph-sdk";
import type { LangChainMessage } from "@assistant-ui/react-langgraph";

export const createClient = () => {
  const apiUrl =
    process.env.NEXT_PUBLIC_LANGGRAPH_API_URL ||
    (typeof window !== "undefined"
      ? new URL("/api", window.location.href).href
      : "/api");
  return new Client({ apiUrl });
};

/**
 * Resolve the checkpoint to fork from when regenerating (Refresh) or editing a message.
 *
 * The LangGraph runtime only enables `onReload`/`onEdit` when a `getCheckpointId` is provided.
 * Canonical assistant-ui pattern: pick the (newest) thread checkpoint whose committed message
 * count equals the truncated parent's, so re-running forks from just before that point. Returns
 * null when no exact-count checkpoint exists — the runtime then re-runs without a fork (graceful).
 */
export const createGetCheckpointId =
  (client: Client) =>
  async (
    threadId: string,
    parentMessages: LangChainMessage[],
  ): Promise<string | null> => {
    const history = await client.threads.getHistory<{ messages?: unknown[] }>(
      threadId,
      { limit: 100 },
    );
    const match = history.find(
      (state) => (state.values?.messages?.length ?? -1) === parentMessages.length,
    );
    return match?.checkpoint?.checkpoint_id ?? null;
  };
