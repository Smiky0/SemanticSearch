import { describe, it, expect } from "vitest";
import {
  RepositorySchema,
  SearchResultSchema,
  ModelConfigSchema,
  GraphDataSchema,
  EdgeTypeEnum,
  SymbolTypeEnum,
  IndexingStatusEnum,
} from "./schemas";

describe("SymbolTypeEnum", () => {
  it("accepts valid symbol types", () => {
    expect(SymbolTypeEnum.parse("function")).toBe("function");
    expect(SymbolTypeEnum.parse("class")).toBe("class");
    expect(SymbolTypeEnum.parse("method")).toBe("method");
  });

  it("rejects invalid symbol types", () => {
    expect(() => SymbolTypeEnum.parse("banana")).toThrow();
  });
});

describe("EdgeTypeEnum", () => {
  it("accepts valid edge types", () => {
    expect(EdgeTypeEnum.parse("calls")).toBe("calls");
    expect(EdgeTypeEnum.parse("imports")).toBe("imports");
    expect(EdgeTypeEnum.parse("inherits")).toBe("inherits");
  });

  it("rejects invalid edge types", () => {
    expect(() => EdgeTypeEnum.parse("jumps")).toThrow();
  });
});

describe("IndexingStatusEnum", () => {
  it("accepts all statuses", () => {
    for (const s of ["pending", "indexing", "completed", "failed"]) {
      expect(IndexingStatusEnum.parse(s)).toBe(s);
    }
  });
});

describe("RepositorySchema", () => {
  const valid = {
    id: "abc-123",
    path: "/host/users/Code/repo",
    name: "repo",
    status: "completed",
    indexed_at: "2026-01-01T00:00:00Z",
    created_at: "2026-01-01T00:00:00Z",
    file_count: 5,
    symbol_count: 10,
    error_message: null,
  };

  it("parses a valid repository", () => {
    const repo = RepositorySchema.parse(valid);
    expect(repo.name).toBe("repo");
    expect(repo.file_count).toBe(5);
  });

  it("rejects invalid status", () => {
    expect(() => RepositorySchema.parse({ ...valid, status: "nope" })).toThrow();
  });

  it("allows nullable indexed_at and error_message", () => {
    const repo = RepositorySchema.parse({ ...valid, indexed_at: null });
    expect(repo.indexed_at).toBeNull();
  });
});

describe("SearchResultSchema", () => {
  it("parses a valid search result", () => {
    const result = SearchResultSchema.parse({
      node: {
        id: "1",
        file_path: "src/main.py",
        language: "python",
        symbol_name: "main",
        symbol_type: "function",
        parent_symbol_id: null,
        start_line: 1,
        end_line: 3,
        source_code: "def main():\n    pass\n",
        docstring: null,
      },
      score: 0.93,
    });
    expect(result.score).toBe(0.93);
    expect(result.node.symbol_name).toBe("main");
  });

  it("rejects a negative-invalid score type", () => {
    expect(() =>
      SearchResultSchema.parse({
        node: {
          id: "1",
          file_path: "a.py",
          language: "python",
          symbol_name: "x",
          symbol_type: "function",
          parent_symbol_id: null,
          start_line: 1,
          end_line: 1,
          source_code: "def x(): pass",
          docstring: null,
        },
        score: "high",
      }),
    ).toThrow();
  });
});

describe("ModelConfigSchema", () => {
  it("applies defaults for optional fields", () => {
    const model = ModelConfigSchema.parse({
      id: "m-local",
      name: "local-llm",
      type: "local",
      provider: "ollama",
    });
    expect(model.llm_max_tokens).toBe(8192);
    expect(model.llm_temperature).toBe(0.7);
    expect(model.embedding_dimensions).toBe(768);
    expect(model.timeout).toBe(120);
    expect(model.active).toBe(false);
  });

  it("accepts full model configs", () => {
    const model = ModelConfigSchema.parse({
      id: "m1",
      name: "ai",
      type: "cloud",
      provider: "gemini",
      api_key: "secret",
      llm_model: "gemini-2.5-flash",
      embedding_model: "text-embedding-004",
      active: true,
    });
    expect(model.api_key).toBe("secret");
    expect(model.active).toBe(true);
  });

  it("rejects unknown provider", () => {
    expect(() =>
      ModelConfigSchema.parse({ name: "x", type: "cloud", provider: "unknown" }),
    ).toThrow();
  });
});

describe("GraphDataSchema", () => {
  it("parses a graph with nodes and edges", () => {
    const graph = GraphDataSchema.parse({
      nodes: [
        { id: "n1", label: "main", symbol_type: "function", file_path: "a.py" },
        { id: "n2", label: "helper", symbol_type: "function", file_path: "a.py" },
      ],
      edges: [{ id: "e1", source: "n1", target: "n2", label: "calls" }],
    });
    expect(graph.nodes).toHaveLength(2);
    expect(graph.edges).toHaveLength(1);
  });

  it("rejects an edge with invalid label", () => {
    expect(() =>
      GraphDataSchema.parse({
        nodes: [],
        edges: [{ id: "e1", source: "a", target: "b", label: "wat" }],
      }),
    ).toThrow();
  });
});
