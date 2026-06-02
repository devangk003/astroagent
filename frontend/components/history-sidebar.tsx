"use client";

import type { FC } from "react";
import { useState } from "react";
import {
  ThreadListItemPrimitive,
  ThreadListPrimitive,
  useAuiState,
  useThreadListItem,
} from "@assistant-ui/react";
import { MenuIcon, PlusIcon, Trash2Icon, XIcon } from "lucide-react";
import { cn } from "@/lib/utils";
import { ProfilesPanel } from "@/components/profiles-panel";

function relativeDate(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const m = Math.floor(diff / 60_000);
  if (m < 1) return "just now";
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  const d = Math.floor(h / 24);
  if (d < 7) return `${d}d ago`;
  return new Date(iso).toLocaleDateString();
}

export const HistorySidebar: FC = () => {
  const [open, setOpen] = useState(false);

  return (
    <>
      {/* Mobile hamburger */}
      <button
        onClick={() => setOpen(true)}
        aria-label="Open session history"
        className="fixed left-3 top-3.5 z-50 rounded-md p-1.5 text-foreground transition-colors hover:bg-accent md:hidden"
      >
        <MenuIcon className="size-5" />
      </button>

      {/* Mobile backdrop */}
      {open && (
        <div
          aria-hidden
          className="fixed inset-0 z-30 bg-black/25 backdrop-blur-sm md:hidden"
          onClick={() => setOpen(false)}
        />
      )}

      {/* Sidebar panel */}
      <aside
        className={cn(
          "flex h-full w-64 flex-shrink-0 flex-col border-r border-border bg-sidebar",
          "fixed inset-y-0 left-0 z-40 md:relative md:z-auto md:translate-x-0",
          "transition-transform duration-200 ease-in-out",
          open ? "translate-x-0" : "-translate-x-full md:translate-x-0",
        )}
      >
        {/* Brand header — height fixed at h-14; logo + text enlarged to fill it (with padding). */}
        <div className="flex h-14 shrink-0 items-center gap-2.5 border-b border-border px-4 py-2">
          <img src="/logo.svg" alt="" className="h-full w-auto select-none" draggable={false} />
          <span className="text-2xl font-semibold tracking-wide text-sidebar-foreground">
            Astro Agent
          </span>
          <button
            onClick={() => setOpen(false)}
            aria-label="Close sidebar"
            className="ml-auto rounded p-1 text-sidebar-foreground transition-colors hover:bg-sidebar-accent md:hidden"
          >
            <XIcon className="size-4" />
          </button>
        </div>

        {/* Thread list */}
        <ThreadListPrimitive.Root className="flex flex-1 flex-col overflow-hidden">
          {/* New session */}
          <div className="shrink-0 px-3 py-3">
            <ThreadListPrimitive.New asChild>
              <button className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium bg-primary text-primary-foreground transition-colors hover:bg-primary/90">
                <PlusIcon className="size-4 shrink-0" />
                New session
              </button>
            </ThreadListPrimitive.New>
          </div>

          {/* Saved profiles */}
          <ProfilesPanel onNavigate={() => setOpen(false)} />

          {/* Session list */}
          <div className="no-scrollbar flex-1 overflow-y-auto px-2 pb-4">
            <p className="px-2 pb-1 pt-0.5 text-[10px] font-semibold uppercase tracking-widest text-muted-foreground">
              Recent
            </p>
            <ThreadListPrimitive.Items>
              {() => <SessionRow onNavigate={() => setOpen(false)} />}
            </ThreadListPrimitive.Items>
          </div>
        </ThreadListPrimitive.Root>
      </aside>
    </>
  );
};

const SessionRow: FC<{ onNavigate: () => void }> = ({ onNavigate }) => {
  const title = useThreadListItem((s) => s.title);
  const custom = useThreadListItem((s) => s.custom);
  const isActive = useAuiState(
    (s) => s.threads.mainThreadId === s.threadListItem.id,
  );
  const createdAt = custom?.createdAt as string | undefined;

  return (
    <ThreadListItemPrimitive.Root className="group relative mb-0.5">
      <ThreadListItemPrimitive.Trigger
        onClick={onNavigate}
        className={cn(
          "flex w-full flex-col items-start rounded-lg px-3 py-2.5 text-left transition-colors",
          "hover:bg-sidebar-accent hover:text-sidebar-accent-foreground",
          isActive && "bg-sidebar-accent text-sidebar-accent-foreground",
        )}
      >
        <span className="w-full truncate text-sm leading-snug text-sidebar-foreground">
          {title ?? "New session"}
        </span>
        {createdAt && (
          <span className="mt-0.5 text-[11px] text-muted-foreground">
            {relativeDate(createdAt)}
          </span>
        )}
      </ThreadListItemPrimitive.Trigger>

      <ThreadListItemPrimitive.Delete asChild>
        <button
          aria-label="Delete session"
          className="absolute right-1 top-1/2 -translate-y-1/2 rounded p-1.5 opacity-0 transition-all hover:text-destructive group-hover:opacity-100"
        >
          <Trash2Icon className="size-3.5" />
        </button>
      </ThreadListItemPrimitive.Delete>
    </ThreadListItemPrimitive.Root>
  );
};
