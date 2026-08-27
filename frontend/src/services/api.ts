import {
  RepositorySchema,
  IndexingStatusResponseSchema,
  SearchResultSchema,
  LLMResponseSchema,
  GraphDataSchema,
  NodeInfoSchema,
  RelationshipSchema,
  type SymbolType,
  type ModelConfig,
} from "../schemas";

const BASE = "/api";

class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (options?.headers) {
    Object.assign(headers, options.headers);
  }

  const res = await fetch(`${BASE}${path}`, { ...options, headers });

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    const message = body.error || body.detail || `Request failed (${res.status})`;
    throw new ApiError(message, res.status);
  }

  return res.json();
}

function parse<T>(schema: { parse: (v: unknown) => T }, data: unknown): T {
  return schema.parse(data);
}

export const api = {
  indexRepository: async (path: string) => {
    const data = await request<unknown>("/repositories/index", {
      method: "POST",
      body: JSON.stringify({ path }),
    });
    return parse(RepositorySchema, data);
  },

  listRepositories: async () => {
    const data = await request<unknown[]>("/repositories");
    return data.map((r) => parse(RepositorySchema, r));
  },

  deleteRepository: async (repoId: string) => {
    const data = await request<unknown>(`/repositories/${repoId}`, { method: "DELETE" });
    return data as { status: string };
  },

  getIndexingStatus: async (repoId: string) => {
    const data = await request<unknown>(`/repositories/${repoId}/status`);
    return parse(IndexingStatusResponseSchema, data);
  },

  search: async (repositoryId: string, query: string, limit = 10, symbolType?: SymbolType) => {
    const data = await request<unknown>("/search", {
      method: "POST",
      body: JSON.stringify({
        repository_id: repositoryId,
        query,
        limit,
        ...(symbolType && { symbol_type: symbolType }),
      }),
    });
    const parsed = data as { results: unknown[] };
    return {
      results: parsed.results.map((r) => parse(SearchResultSchema, r)),
    };
  },

  explain: async (repositoryId: string, query: string) => {
    const data = await request<unknown>("/explain", {
      method: "POST",
      body: JSON.stringify({ repository_id: repositoryId, query }),
    });
    return parse(LLMResponseSchema, data);
  },

  trace: async (repositoryId: string, query: string) => {
    const data = await request<unknown>("/trace", {
      method: "POST",
      body: JSON.stringify({ repository_id: repositoryId, query }),
    });
    return parse(LLMResponseSchema, data);
  },

  getSymbol: async (symbolId: string) => {
    const data = await request<unknown>(`/symbols/${symbolId}`);
    return parse(NodeInfoSchema, data);
  },

  getSymbolRelationships: async (symbolId: string) => {
    const data = await request<unknown[]>(`/symbols/${symbolId}/relationships`);
    return data.map((r) => parse(RelationshipSchema, r));
  },

  getGraph: async (repoId: string) => {
    const data = await request<unknown>(`/graph/${repoId}`);
    return parse(GraphDataSchema, data);
  },

  getLlmProvider: async () => {
    const data = await request<{
      active_llm: string;
      active_embedding: string;
      providers: {
        id: string;
        label: string;
        type: string;
        model: string;
        available: boolean;
        error: string | null;
        ollama_models?: string[];
      }[];
    }>("/config/providers");
    return data;
  },

  browseDirectories: async (path: string) => {
    const data = await request<{
      current: string;
      parent: string | null;
      entries: { name: string; path: string; is_git: boolean }[];
    }>(`/repositories/browse?path=${encodeURIComponent(path)}`);
    return data;
  },

  // Model management
  listModels: async () => {
    const data = await request<{ models: ModelConfig[] }>("/models");
    return data.models;
  },

  createModel: async (config: Partial<ModelConfig>) => {
    const data = await request<ModelConfig>("/models", {
      method: "POST",
      body: JSON.stringify(config),
    });
    return data;
  },

  updateModel: async (modelId: string, updates: Partial<ModelConfig>) => {
    const data = await request<ModelConfig>(`/models/${modelId}`, {
      method: "PUT",
      body: JSON.stringify(updates),
    });
    return data;
  },

  deleteModel: async (modelId: string) => {
    const data = await request<{ status: string }>(`/models/${modelId}`, {
      method: "DELETE",
    });
    return data;
  },

  activateModel: async (modelId: string) => {
    const data = await request<ModelConfig>(`/models/${modelId}/activate`, {
      method: "POST",
    });
    return data;
  },

  checkModelHealth: async (modelId: string) => {
    const data = await request<{
      available: boolean;
      models?: string[];
      error?: string;
    }>(`/models/${modelId}/health`);
    return data;
  },

  setLlmProvider: async (provider: string) => {
    const data = await request<{ active_llm: string; active_embedding: string }>(
      "/config/providers",
      {
        method: "PUT",
        body: JSON.stringify({ provider }),
      },
    );
    return data;
  },
};
