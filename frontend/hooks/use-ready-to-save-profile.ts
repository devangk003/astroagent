"use client";
import { useAuiState } from "@assistant-ui/react";
import { useMemo } from "react";

/**
 * Detects whether the current thread has a reading worth saving as a profile.
 * It is "ready" once any assistant message contains a `compute_birth_chart`
 * tool call — the same signal saveCurrentProfile() relies on server-side
 * (lastComputeBirthChartArgs). This is the reactive frontend trigger for the
 * save-profile pill.
 */
export function useReadyToSaveProfile(): boolean {
  const messages = useAuiState((state) => state.thread.messages);

  return useMemo(() => {
    for (let i = messages.length - 1; i >= 0; i--) {
      const msg = messages[i];
      if (msg.role !== "assistant") continue;
      const parts = msg.content ?? [];
      // "compute_birth_chart" must match the backend tool name exactly
      // (see backend/src/agent/tools/__init__.py). Keep both in sync.
      const hasChart = parts.some(
        (part: any) =>
          part?.type === "tool-call" && part?.toolName === "compute_birth_chart"
      );
      if (hasChart) return true;
    }
    return false;
  }, [messages]);
}
