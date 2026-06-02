"use client";

import { useEffect, useRef, useState } from "react";
import { CircleUserRound, Plus } from "lucide-react";
import { TooltipIconButton } from "@/components/tooltip-icon-button";
import { useSavedProfiles, setAttachedProfile } from "@/lib/profiles";
import { cn } from "@/lib/utils";

/** Composer button (beside "add attachment") to attach a saved birth profile to the next message. */
export function ComposerAttachProfile() {
  const profiles = useSavedProfiles();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    function onDown(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onDown);
    return () => document.removeEventListener("mousedown", onDown);
  }, [open]);

  if (profiles.length === 0) return null; // nothing to attach yet

  return (
    <div ref={ref} className="relative">
      <TooltipIconButton
        tooltip="Attach a saved profile"
        side="bottom"
        type="button"
        variant="ghost"
        size="icon"
        className="size-8 rounded-full p-1 hover:bg-muted-foreground/15"
        aria-label="Attach a saved profile"
        onClick={() => setOpen((o) => !o)}
      >
        <CircleUserRound className="size-5 stroke-[1.5px]" />
      </TooltipIconButton>

      {open && (
        <div className="absolute bottom-full left-0 z-50 mb-2 w-60 max-w-[calc(100vw-2rem)] rounded-xl border border-border bg-popover p-1.5 shadow-lg">
          <p className="px-2 pb-1 pt-0.5 text-[10px] font-semibold uppercase tracking-widest text-muted-foreground">
            Attach profile
          </p>
          {profiles.map((p) => (
            <button
              key={p.id}
              onClick={() => {
                setAttachedProfile(p);
                setOpen(false);
              }}
              className={cn(
                "flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left transition-colors",
                "hover:bg-accent hover:text-accent-foreground",
              )}
            >
              <Plus className="size-4 shrink-0 text-muted-foreground" />
              <span className="flex min-w-0 flex-col">
                <span className="w-full truncate text-sm">{p.label}</span>
                <span className="w-full truncate text-[11px] text-muted-foreground">
                  {p.birthDetails.day}/{p.birthDetails.month}/{p.birthDetails.year}
                  {p.birthDetails.place ? ` · ${p.birthDetails.place}` : ""}
                </span>
              </span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
