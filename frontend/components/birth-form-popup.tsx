"use client";

import { useCallback, useState } from "react";
import { useLangGraphSend } from "@assistant-ui/react-langgraph";
import { BirthForm } from "@/components/birth-form";
import { usePendingBirthRequest } from "@/hooks/use-pending-birth-request";
import { XIcon } from "lucide-react";

/**
 * Birth-form popup panel rendered just above the composer.
 *
 * This is a regular flow element (not absolute) with a card-like
 * appearance so it visually "pops" above the chatbox. It spans
 * the full thread width. It is NOT dismissible by clicking outside —
 * only via the Cancel button.
 */
export function BirthFormPopup() {
  const isPending = usePendingBirthRequest();
  const send = useLangGraphSend();
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = useCallback(
    async (message: string) => {
      setError(null);
      try {
        await send([{ type: "human", content: message }], {});
      } catch (err) {
        setError(
          err instanceof Error ? err.message : "Failed to send. Please try again."
        );
        // Re-throw so the form can handle local submitting state
        throw err;
      }
    },
    [send]
  );

  const handleCancel = useCallback(async () => {
    setError(null);
    try {
      await send([{ type: "human", content: "Cancel" }], {});
    } catch {
      /* noop */
    }
  }, [send]);

  if (!isPending) return null;

  return (
    <div className="z-10 mb-3 w-full max-w-(--thread-max-width) self-center rounded-2xl border bg-background p-4 shadow-xl shadow-black/5 transition-all animate-in fade-in slide-in-from-bottom-2 duration-300">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-base font-semibold tracking-wide text-foreground">
          Birth Details Needed
        </h3>
        <button
          onClick={handleCancel}
          className="ml-4 shrink-0 rounded-full p-1.5 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
          aria-label="Cancel"
        >
          <XIcon className="size-4" />
        </button>
      </div>

      <BirthForm onSubmit={handleSubmit} showNameField={true} />

      {error && (
        <p className="mt-2 text-center text-sm text-red-500">{error}</p>
      )}
    </div>
  );
}
