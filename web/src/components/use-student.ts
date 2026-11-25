"use client";
import { useCallback, useEffect, useState } from "react";
import { api, profileApi, toEngineProfile, type Health, type Profile, type StoredProfile } from "@/lib/client";

export type StudentState = {
  loading: boolean;
  health: Health | null;          // null = engine not reachable
  taxonomy: Record<string, string>;
  stored: StoredProfile | null;    // what's saved locally
  profile: Profile | null;         // complete profile the engine can score, or null
  reload: () => void;
};

/** Engine status, skill taxonomy and the student's saved profile, loaded once per page. */
export function useStudent(): StudentState {
  const [loading, setLoading] = useState(true);
  const [health, setHealth] = useState<Health | null>(null);
  const [taxonomy, setTaxonomy] = useState<Record<string, string>>({});
  const [stored, setStored] = useState<StoredProfile | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    const [h, t, p] = await Promise.all([
      api.health().catch(() => null),
      api.taxonomy().catch(() => ({})),
      profileApi.get().catch(() => null),
    ]);
    setHealth(h);
    setTaxonomy(t);
    setStored(p);
    setLoading(false);
  }, []);
  useEffect(() => { load(); }, [load]);

  return { loading, health, taxonomy, stored, profile: toEngineProfile(stored), reload: load };
}
