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
import { createClient, createGetCheckpointId } from "@/lib/chatApi";
import { createLangGraphThreadAdapter } from "@/lib/thread-adapter";
import { Thread } from "@/components/thread";
import { HistorySidebar } from "@/components/history-sidebar";
import { BirthFormPopup } from "@/components/birth-form-popup";
import {
  ModelConfigContext,
  DEFAULT_MODEL_CONFIG,
  type ModelConfig,
} from "@/context/model-config-context";
import { ProfileContext } from "@/context/profile-context";
import {
  saveProfile,
  setActiveThreadId,
  getActiveThreadId,
  setAttachedProfile,
  getAttachedProfile,
  clearAttachedProfile,
  markMessageProfile,
  profileToMessage,
  type BirthDetails,
  type SavedProfile,
} from "@/lib/profiles";

type ChartArgs = {
  year?: number; month?: number; day?: number;
  hour?: number | null; minute?: number | null;
  lat?: number | null; lng?: number | null; tz?: string | null;
};

/** Find the most recent compute_birth_chart tool-call args in a thread's messages.
 *  This is the authoritative birth data whenever a reading happened — even if the user TYPED
 *  their details (so the strict birth_details regex never matched). Handles both the normalized
 *  LangChain tool_calls shape ({name, args}) and the OpenAI shape (additional_kwargs.tool_calls
 *  with {function:{name, arguments:string}}). */
function lastComputeBirthChartArgs(messages: unknown[] | undefined): ChartArgs | null {
  if (!Array.isArray(messages)) return null;
  for (let i = messages.length - 1; i >= 0; i--) {
    const m = messages[i] as {
      tool_calls?: unknown[];
      additional_kwargs?: { tool_calls?: unknown[] };
    } | null;
    const calls = m?.tool_calls ?? m?.additional_kwargs?.tool_calls;
    if (!Array.isArray(calls)) continue;
    for (const raw of calls) {
      const c = raw as {
        name?: string;
        args?: unknown;
        function?: { name?: string; arguments?: unknown };
      };
      if ((c.name ?? c.function?.name) !== "compute_birth_chart") continue;
      let args: unknown = c.args ?? c.function?.arguments;
      if (typeof args === "string") {
        try {
          args = JSON.parse(args);
        } catch {
          args = null;
        }
      }
      if (args && typeof args === "object") return args as ChartArgs;
    }
  }
  return null;
}

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
  // Enables onReload (Refresh) AND onEdit (pencil) in the LangGraph runtime.
  const getCheckpointId = useMemo(() => createGetCheckpointId(client), [client]);

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
    async (messages, config) => {
      const mc = modelConfigRef.current;
      // Only send fields the user EXPLICITLY set. Empty fields are omitted so the backend's
      // .env defaults (DEFAULT_PROVIDER / DEFAULT_MODEL + the provider key) remain authoritative.
      const configurable: Record<string, string> = {};
      if (mc.provider) configurable.provider = mc.provider;
      if (mc.model) configurable.model = mc.model;
      if (mc.apiKey) configurable.api_key = mc.apiKey;

      // If a saved profile is attached, inject its details into the outgoing human message so the
      // agent receives them (the proven, message-based path — no thread-state seeding).
      let outMessages = messages;
      const attached = getAttachedProfile();
      if (attached) {
        const block = profileToMessage(attached);
        const idx = [...messages].reverse().findIndex((m) => (m as { type?: string }).type === "human");
        if (idx !== -1) {
          const realIdx = messages.length - 1 - idx;
          // Tag this message id so the bubble shows the profile chip consistently — even on the
          // optimistic copy (raw text), before the injected/persisted content reconciles in.
          const msgId = (messages[realIdx] as { id?: string }).id;
          if (msgId) markMessageProfile(msgId, attached.label ?? null);
          outMessages = messages.map((m, i) => {
            if (i !== realIdx) return m;
            const content = (m as { content?: unknown }).content;
            const text = typeof content === "string" ? content : "";
            return { ...m, content: `${block}\n\n${text}`.trim() } as LangChainMessage;
          });
        }
        clearAttachedProfile();
      }

      return baseStream(outMessages, {
        ...config,
        runConfig: { configurable },
      });
    },
    [baseStream],
  );

  const runtime = useLangGraphRuntime({
    unstable_threadListAdapter: threadAdapter,
    unstable_allowCancellation: true,
    getCheckpointId,
    stream,
    create: async () => {
      // NOTE: ignored when a thread-list adapter is present (the adapter's initialize() creates
      // threads). Profile reuse is via message-injection in the stream wrapper, not state-seeding.
      const { thread_id } = await client.threads.create();
      setActiveThreadId(thread_id);
      return { externalId: thread_id };
    },
    load: async (externalId) => {
      setActiveThreadId(externalId);
      const state = await client.threads.getState<{
        messages: LangChainMessage[];
      }>(externalId);
      return {
        messages: state.values.messages,
        interrupts: state.tasks[0]?.interrupts,
      };
    },
  });

  // ── Saved-profile actions (need the client + runtime) ──
  const saveCurrentProfile = useCallback(
    async (label?: string) => {
      const tid = getActiveThreadId();
      if (!tid) throw new Error("Open a chat first.");
      const state = await client.threads.getState<{
        birth_details?: BirthDetails | null;
        chart?: unknown;
        messages?: unknown[];
      }>(tid);

      // birth_details is only set when a message matched the strict birth-sentence regex (the
      // form's format). For TYPED details it's null — but whenever a reading happened the agent
      // called compute_birth_chart with the structured args, so use those as the authoritative
      // source and merge name/place from birth_details when available.
      const bd = (state.values?.birth_details ?? {}) as Partial<BirthDetails>;
      const args = lastComputeBirthChartArgs(state.values?.messages);
      if (!state.values?.birth_details && !args) {
        throw new Error("No reading found in this chat yet — ask for your chart first, then save.");
      }
      const pick = <T,>(a: T | null | undefined, b: T | null | undefined): T | null =>
        a ?? b ?? null;
      const profile: BirthDetails = {
        name: bd.name ?? null,
        year: (pick(bd.year, args?.year) as number),
        month: (pick(bd.month, args?.month) as number),
        day: (pick(bd.day, args?.day) as number),
        hour: pick(bd.hour, args?.hour),
        minute: pick(bd.minute, args?.minute),
        unknown_time: bd.unknown_time ?? (args ? args.hour == null : false),
        place: bd.place ?? "",
        lat: pick(bd.lat, args?.lat),
        lng: pick(bd.lng, args?.lng),
        tz: pick(bd.tz, args?.tz),
      };
      if (profile.year == null) {
        throw new Error("Couldn't read your birth date from this chat — try again after a reading.");
      }
      saveProfile({
        id: globalThis.crypto?.randomUUID?.() ?? String(Date.now()),
        label: label?.trim() || profile.name || profile.place || "Profile",
        createdAt: new Date().toISOString(),
        birthDetails: profile,
        chart: state.values?.chart,
      });
    },
    [client],
  );

  const startWithProfile = useCallback(
    (p: SavedProfile) => {
      setAttachedProfile(p); // chip appears in the composer; injected on the first send
      runtime.threads.switchToNewThread();
    },
    [runtime],
  );

  return (
    <ModelConfigContext.Provider
      value={{ config: modelConfig, setConfig: handleSetConfig }}
    >
      <ProfileContext.Provider value={{ saveCurrentProfile, startWithProfile }}>
        <AssistantRuntimeProvider runtime={runtime}>
          <RequestBirthDetailsUI />
          <div className="flex h-dvh overflow-hidden">
            <HistorySidebar />
            <div className="flex-1 min-w-0">
              <Thread />
            </div>
          </div>
        </AssistantRuntimeProvider>
      </ProfileContext.Provider>
    </ModelConfigContext.Provider>
  );
}
