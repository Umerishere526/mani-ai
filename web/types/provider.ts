// ABOUTME: Types for the admin Providers section — LLM provider configuration.
// ABOUTME: Ported from mani-app's lib/schema/providers.ts and lib/providers/types.ts.

export interface Provider {
  id: string;
  name: string;
  displayName: string;
  apiKey: string | null;
  baseUrl: string | null;
  config: Record<string, unknown>;
  createdAt: string;
  updatedAt: string;
}

/** Provider list item — excludes the API key, used for list views. */
export type ProviderListItem = Omit<Provider, "apiKey"> & {
  hasApiKey: boolean;
};

/** A model available from a provider's API. */
export interface Model {
  id: string;
  name: string;
  provider: string;
  created?: number;
  ownedBy?: string;
  object?: string;
}
