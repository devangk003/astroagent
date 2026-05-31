"use client";
import { useAuiState } from "@assistant-ui/react";
import { useMemo } from "react";

/**
 * Detects whether the assistant is waiting for the user to fill out the
 * birth-details popup form.  It is "pending" when the most recent assistant
 * message contains a `request_birth_details` tool call and no human message
 * has been sent after it.
 */
export function usePendingBirthRequest() {
  const messages = useAuiState((state) => state.thread.messages);

  return useMemo(() => {
    // Scan backwards from the most recent message
    for (let i = messages.length - 1; i >= 0; i--) {
      const msg = messages[i];
      if (msg.role === "user") {
        // Found a user message — if it's after any assistant request, the
        // popup is no longer pending (user already responded).
        return false;
      }
      if (msg.role === "assistant") {
        // Check if this assistant message contains a request_birth_details
        // tool call anywhere in its content parts.
        const parts = msg.content ?? [];
        // "request_birth_details" must match the backend tool name exactly
        // (see backend/src/agent/tools/__init__.py). Keep both in sync.
        const hasBirthRequest = parts.some(
          (part: any) =>
            part?.type === "tool-call" && part?.toolName === "request_birth_details"
        );
        if (hasBirthRequest) {
          // Assistant asked for birth details and no newer user message
          // was found (we hit this before any user message), so pending.
          return true;
        }
      }
    }
    return false;
  }, [messages]);
}
