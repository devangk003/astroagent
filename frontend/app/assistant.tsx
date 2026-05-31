"use client";

import { useCallback, useMemo, useRef, useState } from "react";
import { AssistantRuntimeProvider } from "@assistant-ui/react";
import {
  unstable_createLangGraphStream,
  useLangGraphRuntime,
  type LangChainMessage,
  type LangGraphStreamCallback,
} from "@assistant-ui/react-langgraph";

import { makeAssistantToolUI } from "@assistant-ui/react";
import { createClient } from "@/lib/chatApi";
import { createLangGraphThreadAdapter } from "@/lib/thread-adapter";
import { Thread } from "@/components/thread";
import { HistorySidebar } from "@/components/history-sidebar";
import { BirthFormPopup } from "@/components/birth-form-popup";
import {
  ModelConfigContext,
  DEFAULT_MODEL_CONFIG,
  type ModelConfig,
} from "@/context/model-config-context";

const ASSISTANT_ID =
  process.env.NEXT_PUBLIC_LANGGRAPH_ASSISTANT_ID ?? "astro_agent";

const RequestBirthDetailsUI = makeAssistantToolUI<{ needs_name?: boolean }, string>({
  toolName: "request_birth_details",
  render: () => (
    <div className="my-1 flex items-center gap-1.5 text-xs text-muted-foreground">
      <span className="inline-block h-1.5 w-1.5 rounded-full bg-amber-400" />
      Waiting for birth details…
    </div>
  ),
});

export function Assistant() {
  const client = useMemo(() => createClient(), []);
  const threadAdapter = useMemo(
    () => createLangGraphThreadAdapter(client),
    [client],
  );

  // Model config: state for the UI (model selector), ref for the stream callback.
  const [modelConfig, setModelConfigState] = useState<ModelConfig>(DEFAULT_MODEL_CONFIG);
  const modelConfigRef = useRef<ModelConfig>(modelConfig);

  function handleSetConfig(cfg: ModelConfig) {
    modelConfigRef.current = cfg;
    setModelConfigState(cfg);
  }

  // Base stream created once; the wrapper below always injects current model config.
  const baseStream = useMemo(
    () => unstable_createLangGraphStream({ client, assistantId: ASSISTANT_ID }),
    [client],
  );

  // Wrapper: inject current model config as runConfig so every run — birth-form
  // or composer — uses the BYOK provider/model the user selected.
  const stream = useCallback<LangGraphStreamCallback<LangChainMessage>>(
    (messages, config) => {
      const mc = modelConfigRef.current;
      return baseStream(messages, {
        ...config,
        runConfig: {
          configurable: {
            provider: mc.provider,
            model: mc.model,
            ...(mc.apiKey ? { api_key: mc.apiKey } : {}),
          },
        },
      });
    },
    [baseStream],
  );

  const runtime = useLangGraphRuntime({
    unstable_threadListAdapter: threadAdapter,
    unstable_allowCancellation: true,
    stream,
    create: async () => {
      const { thread_id } = await client.threads.create();
      return { externalId: thread_id };
    },
    load: async (externalId) => {
      const state = await client.threads.getState<{
        messages: LangChainMessage[];
      }>(externalId);
      return {
        messages: state.values.messages,
        interrupts: state.tasks[0]?.interrupts,
      };
    },
  });

  return (
    <ModelConfigContext.Provider
      value={{ config: modelConfig, setConfig: handleSetConfig }}
    >
      <AssistantRuntimeProvider runtime={runtime}>
        <RequestBirthDetailsUI />
        <div className="flex h-dvh overflow-hidden">
          <HistorySidebar />
          <div className="flex-1 min-w-0">
            <Thread />
          </div>
        </div>
      </AssistantRuntimeProvider>
    </ModelConfigContext.Provider>
  );
}
