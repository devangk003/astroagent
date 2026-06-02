"use client";

import { useCallback, useState } from "react";
import { CircleUserRound } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useReadyToSaveProfile } from "@/hooks/use-ready-to-save-profile";
import { usePendingBirthRequest } from "@/hooks/use-pending-birth-request";
import { useProfileActions } from "@/context/profile-context";
import {
  getActiveThreadId,
  dismissSavePill,
  useSavePillDismissed,
} from "@/lib/profiles";

/**
 * Pill that slides up just above the composer once a reading is ready, offering to
 * save the conversation's birth details as a profile. Mirrors BirthFormPopup's width,
 * radius, spacing and animation so it reads as a sibling of the chatbox.
 *
 * - Visible only when a reading exists (compute_birth_chart ran) AND the pill hasn't been
 *   dismissed/saved for this thread this session, AND the birth form isn't pending.
 * - Save → saveCurrentProfile() then dismiss; Cancel → dismiss only (won't reappear this session).
 */
export function SaveProfilePill() {
  const ready = useReadyToSaveProfile();
  const pendingForm = usePendingBirthRequest();
  const tid = getActiveThreadId();
  const dismissed = useSavePillDismissed(tid);
  const { saveCurrentProfile } = useProfileActions();
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSave = useCallback(async () => {
    setError(null);
    setSaving(true);
    try {
      await saveCurrentProfile();
      dismissSavePill(getActiveThreadId());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Couldn't save");
    } finally {
      setSaving(false);
    }
  }, [saveCurrentProfile]);

  const handleCancel = useCallback(() => {
    dismissSavePill(getActiveThreadId());
  }, []);

  if (!ready || dismissed || pendingForm) return null;

  return (
    <div className="z-10 mb-3 flex w-full max-w-(--thread-max-width) items-center justify-between gap-3 self-center rounded-2xl border bg-background px-4 py-2.5 shadow-xl shadow-black/5 transition-all animate-in fade-in slide-in-from-bottom-2 duration-300">
      <div className="flex min-w-0 items-center gap-2 text-sm text-foreground">
        <CircleUserRound className="size-4 shrink-0 text-muted-foreground" />
        <span className="truncate">
          {error ?? "Save these birth details as a profile?"}
        </span>
      </div>
      <div className="flex shrink-0 items-center gap-2">
        <Button variant="ghost" size="sm" onClick={handleCancel} disabled={saving}>
          Cancel
        </Button>
        <Button size="sm" onClick={handleSave} disabled={saving}>
          {saving ? "Saving…" : "Save"}
        </Button>
      </div>
    </div>
  );
}
