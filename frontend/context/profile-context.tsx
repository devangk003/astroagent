"use client";

import { createContext, useContext } from "react";
import type { SavedProfile } from "@/lib/profiles";

/** Actions that need the LangGraph client / runtime (provided by app/assistant.tsx). */
export type ProfileActions = {
  /** Save the ACTIVE conversation's birth-details (+ chart) as a profile. Throws if none yet. */
  saveCurrentProfile: (label?: string) => Promise<void>;
  /** Open a fresh conversation pre-seeded with this profile. */
  startWithProfile: (p: SavedProfile) => void;
};

export const ProfileContext = createContext<ProfileActions>({
  saveCurrentProfile: async () => {},
  startWithProfile: () => {},
});

export const useProfileActions = () => useContext(ProfileContext);
