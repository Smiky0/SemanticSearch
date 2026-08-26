import { z } from "zod";

export const SymbolTypeEnum = z.enum(["file", "module", "class", "function", "method"]);
export const EdgeTypeEnum = z.enum(["imports", "calls", "defines", "contains", "references", "inherits"]);
export const IndexingStatusEnum = z.enum(["pending", "indexing", "completed", "failed"]);

export const RepositorySchema = z.object({
  id: z.string(),
  path: z.string(),
  name: z.string(),
  status: IndexingStatusEnum,
  indexed_at: z.string().nullable(),
  created_at: z.string(),
  file_count: z.number(),
  symbol_count: z.number(),
  error_message: z.string().nullable(),
});

export const NodeInfoSchema = z.object({
  id: z.string(),
  file_path: z.string(),
  language: z.string(),
  symbol_name: z.string(),
  symbol_type: SymbolTypeEnum,
  parent_symbol_id: z.string().nullable(),
  start_line: z.number(),
  end_line: z.number(),
  source_code: z.string(),
  docstring: z.string().nullable(),
});

export const SearchResultSchema = z.object({
  node: NodeInfoSchema,
  score: z.number(),
});

export const SourceRefSchema = z.object({
  file_path: z.string(),
  symbol_name: z.string(),
  start_line: z.number(),
  end_line: z.number(),
});

export const LLMResponseSchema = z.object({
  answer: z.string(),
  sources: z.array(SourceRefSchema),
});

export const GraphNodeSchema = z.object({
  id: z.string(),
  label: z.string(),
  symbol_type: SymbolTypeEnum,
  file_path: z.string(),
});

export const GraphEdgeSchema = z.object({
  id: z.string(),
  source: z.string(),
  target: z.string(),
  label: EdgeTypeEnum,
});

export const GraphDataSchema = z.object({
  nodes: z.array(GraphNodeSchema),
  edges: z.array(GraphEdgeSchema),
});

export const RelationshipSchema = z.object({
  source: NodeInfoSchema,
  target: NodeInfoSchema,
  edge_type: EdgeTypeEnum,
});

export const IndexingStatusResponseSchema = z.object({
  repository_id: z.string(),
  status: IndexingStatusEnum,
  file_count: z.number(),
  symbol_count: z.number(),
  error_message: z.string().nullable(),
});

export type SymbolType = z.infer<typeof SymbolTypeEnum>;
export type EdgeType = z.infer<typeof EdgeTypeEnum>;
export type IndexingStatus = z.infer<typeof IndexingStatusEnum>;
export type Repository = z.infer<typeof RepositorySchema>;
export type NodeInfo = z.infer<typeof NodeInfoSchema>;
export type SearchResult = z.infer<typeof SearchResultSchema>;
export type SourceRef = z.infer<typeof SourceRefSchema>;
export type LLMResponse = z.infer<typeof LLMResponseSchema>;
export type GraphData = z.infer<typeof GraphDataSchema>;
export type GraphNodeData = z.infer<typeof GraphNodeSchema>;
export type GraphEdgeData = z.infer<typeof GraphEdgeSchema>;
export type Relationship = z.infer<typeof RelationshipSchema>;
