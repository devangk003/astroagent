"use client";

import { useEffect, useRef, useState } from "react";
import { ChevronDownIcon, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useModelConfig, type ModelConfig } from "@/context/model-config-context";
import { cn } from "@/lib/utils";

const inputCls =
  "w-full rounded-md border border-border bg-background px-3 py-2 text-sm " +
  "placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring";

const PROVIDER_LABELS: Record<string, string> = {
  ollama: "Ollama Cloud",
  openrouter: "OpenRouter",
};

function truncate(str: string, max: number) {
  return str.length > max ? str.slice(0, max) + "…" : str;
}

export function ModelSelectorPill() {
  const { config, setConfig } = useModelConfig();
  const [open, setOpen] = useState(false);
  const [local, setLocal] = useState<ModelConfig>(config);
  const ref = useRef<HTMLDivElement>(null);

  function handleToggle() {
    if (!open) setLocal(config);
    setOpen((o) => !o);
  }

  function handleApply() {
    setConfig(local);
    setOpen(false);
  }

  // Close on outside click
  useEffect(() => {
    if (!open) return;
    function onMouseDown(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", onMouseDown);
    return () => document.removeEventListener("mousedown", onMouseDown);
  }, [open]);

  // Close on Escape
  useEffect(() => {
    if (!open) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open]);

  return (
    <div ref={ref} className="relative">
      {/* ── Pill trigger ── */}
      <button
        onClick={handleToggle}
        aria-expanded={open}
        aria-haspopup="true"
        aria-label="Select AI model"
        title="AI model — click to change"
        className={cn(
          "flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs font-medium transition-colors",
          "border-border bg-muted/40 text-foreground hover:bg-muted",
          open && "bg-muted ring-2 ring-ring/30",
        )}
      >
        {/* Explicit label so the chip's purpose is self-evident (recognition over recall). */}
        <Sparkles className="size-3.5 shrink-0 text-muted-foreground" aria-hidden />
        <span className="text-muted-foreground">Model</span>
        <span className="text-muted-foreground/40">·</span>
        <span className="text-muted-foreground">
          {config.provider ? PROVIDER_LABELS[config.provider] : "Default"}
        </span>
        {config.provider && (
          <>
            <span className="text-muted-foreground/40">·</span>
            <span className="max-w-[120px] truncate">
              {config.model ? truncate(config.model, 18) : "server default"}
            </span>
          </>
        )}
        <ChevronDownIcon
          className={cn(
            "size-3 shrink-0 text-muted-foreground transition-transform duration-150",
            open && "rotate-180",
          )}
        />
      </button>

      {/* ── Dropdown panel ── */}
      {open && (
        <div className="absolute right-0 top-full z-50 mt-2 w-72 max-w-[calc(100vw-2rem)] rounded-xl border border-border bg-popover p-4 shadow-lg flex flex-col gap-4">

          {/* Provider toggle */}
          <div className="flex flex-col gap-2">
            <span className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
              Provider
            </span>
            <div className="flex gap-1 rounded-lg bg-muted p-1">
              {([["", "Default"], ["ollama", "Ollama Cloud"], ["openrouter", "OpenRouter"]] as const).map(
                ([p, label]) => (
                  <button
                    key={p || "default"}
                    onClick={() =>
                      setLocal((c) =>
                        p === "" ? { ...c, provider: "", model: "" } : { ...c, provider: p },
                      )
                    }
                    className={cn(
                      "flex-1 rounded-md px-2 py-1.5 text-xs font-medium transition-colors",
                      local.provider === p
                        ? "bg-background text-foreground shadow-sm"
                        : "text-muted-foreground hover:text-foreground",
                    )}
                  >
                    {label}
                  </button>
                ),
              )}
            </div>
          </div>

          {local.provider === "" ? (
            <p className="text-[11px] text-muted-foreground">
              Using the server&apos;s configured model (backend <code>.env</code> DEFAULT_MODEL).
              Pick a provider above to override it for this session.
            </p>
          ) : (
            <>
              {/* Model string */}
              <div className="flex flex-col gap-1.5">
                <label className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
                  {local.provider === "ollama" ? "Model String" : "Model"}
                </label>
                <input
                  type="text"
                  value={local.model}
                  onChange={(e) => setLocal((c) => ({ ...c, model: e.target.value }))}
                  placeholder={local.provider === "openrouter" ? "qwen/qwen3-235b-a22b" : "kimi-k2.6:cloud"}
                  className={inputCls}
                />
                {local.provider === "ollama" && (
                  <p className="text-[11px] text-muted-foreground">
                    Exact tag shown on Ollama Cloud — e.g. <code>kimi-k2.6:cloud</code>
                  </p>
                )}
              </div>

              {/* API key */}
              <div className="flex flex-col gap-1.5">
                <label className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
                  {local.provider === "ollama" ? "Ollama Cloud Key" : "OpenRouter Key"}
                </label>
                <input
                  type="password"
                  value={local.apiKey}
                  onChange={(e) => setLocal((c) => ({ ...c, apiKey: e.target.value }))}
                  placeholder="Session only — resets on refresh"
                  className={inputCls}
                />
              </div>
            </>
          )}

          <Button onClick={handleApply} size="sm" className="w-full">
            Apply
          </Button>
        </div>
      )}
    </div>
  );
}
