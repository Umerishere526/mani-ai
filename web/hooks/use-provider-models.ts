// ABOUTME: Loads providers on mount and models when the selected provider changes.
// ABOUTME: Reads from placeholder data (see lib/placeholder-providers.ts) behind the same
// ABOUTME: async-shaped state as the real listProviders()/fetch("/api/admin/models") calls,
// ABOUTME: so loading/error UI stays reachable until a real backend replaces this.

import { useEffect, useRef, useState } from "react";
import type { Model, ProviderListItem } from "@/types";
import { PROVIDERS, MODELS_BY_PROVIDER } from "@/lib/placeholder-providers";

interface UseProviderModelsResult {
  providers: ProviderListItem[];
  models: Model[];
  loadingProviders: boolean;
  loadingModels: boolean;
  modelsError: string | null;
}

export function useProviderModels(
  selectedProvider: string | undefined,
  currentModelId: string | undefined,
  onDefaultProvider: (name: string) => void,
  onDefaultModel: (id: string) => void,
): UseProviderModelsResult {
  // Source fetches providers via an async listProviders() call on mount; the placeholder
  // data is synchronous, so it's read directly rather than staged through setState in an
  // effect (no real async gap to synchronize). loadingProviders stays false from the start.
  const [providers] = useState<ProviderListItem[]>(PROVIDERS);
  const loadingProviders = false;

  const didSetDefaultProvider = useRef(false);
  useEffect(() => {
    if (!didSetDefaultProvider.current && providers.length > 0) {
      didSetDefaultProvider.current = true;
      onDefaultProvider(providers[0].name);
    }
    // Runs once on mount, matching source's listProviders() fetch-on-mount behavior.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const models = selectedProvider ? (MODELS_BY_PROVIDER[selectedProvider] ?? []) : [];
  const modelsError =
    selectedProvider && !MODELS_BY_PROVIDER[selectedProvider]
      ? `No models available for provider "${selectedProvider}"`
      : null;

  const lastAppliedProvider = useRef<string | undefined>(undefined);
  useEffect(() => {
    if (lastAppliedProvider.current === selectedProvider) return;
    lastAppliedProvider.current = selectedProvider;

    if (!selectedProvider) {
      onDefaultModel("");
      return;
    }
    const modelExists = models.some((m) => m.id === currentModelId);
    if (!modelExists && models.length > 0) {
      onDefaultModel(models[0].id);
    } else if (models.length === 0) {
      onDefaultModel("");
    }
    // Only re-run when the provider changes, matching source's dependency array.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedProvider]);

  return {
    providers,
    models,
    loadingProviders,
    loadingModels: false,
    modelsError,
  };
}
