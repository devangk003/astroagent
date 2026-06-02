"use client";

import { useState } from "react";
import { LotusBloom } from "@/components/lotus-bloom";

/** Standalone preview for the lotus-bloom animation. Visit http://localhost:3000/bloom */
export default function BloomPage() {
  const [replay, setReplay] = useState(0);
  return (
    <main className="flex min-h-dvh flex-col items-center justify-center gap-10 bg-background">
      <LotusBloom replayKey={replay} size={280} durationMs={1200} />
      <button
        onClick={() => setReplay((n) => n + 1)}
        className="rounded-full border border-border bg-muted/40 px-5 py-2 text-sm font-medium text-foreground transition-colors hover:bg-muted"
      >
        Replay
      </button>
    </main>
  );
}
