import type { RemoteThreadListAdapter } from "@assistant-ui/core";
import type { Client } from "@langchain/langgraph-sdk";
import type { AssistantStream } from "assistant-stream";
import { setActiveThreadId } from "@/lib/profiles";

type RawMsg = { type?: string; role?: string; content?: unknown };

function extractTitle(values: unknown): string | undefined {
  const msgs = ((values as Record<string, unknown>)?.messages ?? []) as RawMsg[];
  const first = msgs.find((m) => m.type === "human" || m.role === "user");
  const raw = first?.content;
  return typeof raw === "string" ? raw.slice(0, 45) || undefined : undefined;
}

export function createLangGraphThreadAdapter(client: Client): RemoteThreadListAdapter {
  return {
    list: async () => {
      const threads = await client.threads.search({
        limit: 50,
        sortBy: "updated_at",
        sortOrder: "desc",
      });
      return {
        threads: threads.map((t) => ({
          status: "regular" as const,
          remoteId: t.thread_id,
          externalId: t.thread_id,
          title: extractTitle(t.values),
          custom: { createdAt: t.created_at },
        })),
      };
    },

    initialize: async () => {
      // Profile reuse is via message-injection in the stream wrapper (app/assistant.tsx), not
      // thread-state seeding — so this just creates the thread and records the active id.
      const { thread_id } = await client.threads.create();
      setActiveThreadId(thread_id);
      return { remoteId: thread_id, externalId: thread_id };
    },

    rename: async (remoteId, newTitle) => {
      await client.threads.update(remoteId, {
        metadata: { title: newTitle },
        returnMinimal: true,
      });
    },

    delete: async (remoteId) => {
      await client.threads.delete(remoteId);
    },

    archive: async () => {},
    unarchive: async () => {},

    generateTitle: async (): Promise<AssistantStream> =>
      new ReadableStream({ start: (c) => c.close() }) as unknown as AssistantStream,

    fetch: async (threadId) => {
      const t = await client.threads.get(threadId);
      return {
        status: "regular" as const,
        remoteId: t.thread_id,
        externalId: t.thread_id,
        title: extractTitle(t.values),
        custom: { createdAt: t.created_at },
      };
    },
  };
}
