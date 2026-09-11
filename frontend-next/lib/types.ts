export type Role = "system" | "user" | "assistant";

export interface ChatMessage {
  role: Role;
  content: string;
}

export interface ColumnMeta {
  name: string;
  dataType?: string;
}

export interface TableMeta {
  name: string;
  description?: string;
  columns: ColumnMeta[];
}

export interface MeasureMeta {
  name: string;
  table?: string;
  expression: string;
  formatString?: string;
}

export interface RelationshipMeta {
  from: string;
  to: string;
  cardinality?: string;
}

export interface ModelSchema {
  name: string;
  source?: string;
  tables: TableMeta[];
  measures: MeasureMeta[];
  relationships?: RelationshipMeta[];
}

export interface AgentInfo {
  id: string;
  name: string;
  mode: "live" | "demo";
  reasoning_model: string;
  dataset_id: string;
  workspace_id: string;
}

/** A tool step the agent reported mid-stream. */
export interface AgentStep {
  tool?: "dax" | "schema";
  name?: string;
  dax?: string;
  purpose?: string;
  columns?: string[];
  rows?: Record<string, unknown>[];
  rowCount?: number;
  truncated?: boolean;
  error?: string;
  table?: string;
}

/** One rendered block inside an assistant turn. */
export type Block =
  | { kind: "note"; text: string }
  | { kind: "query"; step: AgentStep; elapsedMs: number }
  | { kind: "error"; text: string };

export interface Turn {
  id: string;
  question: string;
  blocks: Block[];
  answer: string;
  status: "working" | "done" | "failed";
  elapsedMs?: number;
}
