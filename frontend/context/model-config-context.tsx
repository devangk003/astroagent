"use client";

import { createContext, useContext } from "react";

// Empty provider/model mean "use the backend's .env default" (DEFAULT_PROVIDER/DEFAULT_MODEL).
export type ModelConfig = {
  provider: "openrouter" | "ollama" | "";
  model: string;
  apiKey: string;
};

// Default = UNSET → the backend .env is authoritative. The selector only OVERRIDES once the user
// picks a provider/model (see assistant.tsx: empty fields are not sent). Optional NEXT_PUBLIC_*
// vars let you pre-seed an explicit frontend default, but normally leave them unset so .env wins.
const _ENV_PROVIDER = process.env.NEXT_PUBLIC_DEFAULT_PROVIDER;
const _DEFAULT_PROVIDER: ModelConfig["provider"] =
  _ENV_PROVIDER === "openrouter" || _ENV_PROVIDER === "ollama" ? _ENV_PROVIDER : "";

export const DEFAULT_MODEL_CONFIG: ModelConfig = {
  provider: _DEFAULT_PROVIDER,
  model: process.env.NEXT_PUBLIC_DEFAULT_MODEL || "",
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
