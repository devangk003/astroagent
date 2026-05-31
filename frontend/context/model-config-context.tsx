"use client";

import { createContext, useContext } from "react";

export type ModelConfig = {
  provider: "openrouter" | "ollama";
  model: string;
  apiKey: string;
};

// Initial UI default. Driven by .env (NEXT_PUBLIC_DEFAULT_PROVIDER / NEXT_PUBLIC_DEFAULT_MODEL)
// so no model string is hardcoded as the source of truth; the in-UI selector still supersedes
// this per-session, and an empty apiKey lets the backend fall back to the provider key in .env.
// The literals below are last-resort fallbacks only (kept in sync with backend DEFAULT_*).
const _ENV_PROVIDER = process.env.NEXT_PUBLIC_DEFAULT_PROVIDER;
const _DEFAULT_PROVIDER: ModelConfig["provider"] =
  _ENV_PROVIDER === "openrouter" || _ENV_PROVIDER === "ollama" ? _ENV_PROVIDER : "ollama";

export const DEFAULT_MODEL_CONFIG: ModelConfig = {
  provider: _DEFAULT_PROVIDER,
  model: process.env.NEXT_PUBLIC_DEFAULT_MODEL || "qwen3.5:397b",
  apiKey: "",
};

type ModelConfigContextType = {
  config: ModelConfig;
  setConfig: (cfg: ModelConfig) => void;
};

export const ModelConfigContext = createContext<ModelConfigContextType>({
  config: DEFAULT_MODEL_CONFIG,
  setConfig: () => {},
});

export const useModelConfig = () => useContext(ModelConfigContext);
