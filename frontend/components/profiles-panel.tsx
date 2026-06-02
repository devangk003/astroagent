"use client";

import { useEffect, useRef, useState, type FC } from "react";
import { Trash2Icon, PencilIcon, CheckIcon, XIcon, CircleUserRound } from "lucide-react";
import {
  useSavedProfiles,
  deleteProfile,
  renameProfile,
  type SavedProfile,
} from "@/lib/profiles";
import { useProfileActions } from "@/context/profile-context";
import { cn } from "@/lib/utils";

function summary(p: SavedProfile): string {
  const b = p.birthDetails;
  const date = `${String(b.day).padStart(2, "0")}/${String(b.month).padStart(2, "0")}/${b.year}`;
  return b.place ? `${date} · ${b.place}` : date;
}

/** Sidebar section: list saved birth profiles; start new chats, rename inline, or delete them. */
export const ProfilesPanel: FC<{ onNavigate?: () => void }> = ({ onNavigate }) => {
  const profiles = useSavedProfiles();
  const { startWithProfile } = useProfileActions();
  const [editingId, setEditingId] = useState<string | null>(null);
  const [draft, setDraft] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  // Focus + select the field whenever a row enters edit mode.
  useEffect(() => {
    if (editingId) inputRef.current?.select();
  }, [editingId]);

  function beginEdit(p: SavedProfile) {
    setDraft(p.label);
    setEditingId(p.id);
  }
  function commitEdit() {
    if (editingId && draft.trim()) renameProfile(editingId, draft.trim());
    setEditingId(null);
  }
  function cancelEdit() {
    setEditingId(null);
  }

  // Hide the whole section until at least one profile is saved.
  if (profiles.length === 0) return null;

  return (
    <div className="shrink-0 border-b border-border px-2 pb-3 pt-1">
      <div className="px-2 pb-1">
        <p className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground">
          Saved profiles
        </p>
      </div>

      <ul className="flex flex-col gap-0.5">
        {profiles.map((p) =>
            editingId === p.id ? (
              <li key={p.id} className="flex items-center gap-1 px-2 py-1">
                <input
                  ref={inputRef}
                  value={draft}
                  autoFocus
                  onChange={(e) => setDraft(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") commitEdit();
                    else if (e.key === "Escape") cancelEdit();
                  }}
                  onBlur={commitEdit}
                  className="min-w-0 flex-1 rounded-md border border-border bg-background px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                />
                {/* preventDefault on mousedown so the input's onBlur doesn't fire before the click */}
                <button
                  aria-label="Save name"
                  onMouseDown={(e) => e.preventDefault()}
                  onClick={commitEdit}
                  className="rounded p-1 text-muted-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
                >
                  <CheckIcon className="size-3.5" />
                </button>
                <button
                  aria-label="Cancel rename"
                  onMouseDown={(e) => e.preventDefault()}
                  onClick={cancelEdit}
                  className="rounded p-1 text-muted-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
                >
                  <XIcon className="size-3.5" />
                </button>
              </li>
            ) : (
              <li key={p.id} className="group relative">
                <button
                  onClick={() => {
                    startWithProfile(p);
                    onNavigate?.();
                  }}
                  title={`Start a new chat as ${p.label}`}
                  className={cn(
                    "flex w-full items-center gap-2.5 rounded-lg px-3 py-2 pr-12 text-left transition-colors",
                    "hover:bg-sidebar-accent hover:text-sidebar-accent-foreground",
                  )}
                >
                  <CircleUserRound className="size-4 shrink-0 text-muted-foreground" />
                  <span className="flex min-w-0 flex-col">
                    <span className="w-full truncate text-sm leading-snug">{p.label}</span>
                    <span className="mt-0.5 truncate text-[11px] text-muted-foreground">
                      {summary(p)}
                    </span>
                  </span>
                </button>
                <div className="absolute right-1.5 top-1.5 flex gap-0.5 opacity-0 transition-opacity group-hover:opacity-100">
                  <button
                    aria-label="Rename profile"
                    onClick={() => beginEdit(p)}
                    className="rounded p-1 text-muted-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
                  >
                    <PencilIcon className="size-3.5" />
                  </button>
                  <button
                    aria-label="Delete profile"
                    onClick={() => deleteProfile(p.id)}
                    className="rounded p-1 text-muted-foreground hover:bg-destructive/15 hover:text-destructive"
                  >
                    <Trash2Icon className="size-3.5" />
                  </button>
                </div>
              </li>
            ),
          )}
      </ul>
    </div>
  );
};
