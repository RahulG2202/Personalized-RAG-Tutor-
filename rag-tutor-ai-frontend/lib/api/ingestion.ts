export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export type CeleryTaskState =
  | "PENDING"
  | "STARTED"
  | "SUCCESS"
  | "FAILURE"
  | "RETRY"
  | "REVOKED"
  | string;

export type CeleryTaskStatus<TResult = unknown> = {
  task_id: string;
  state: CeleryTaskState;
  result?: TResult;
  error?: string;
  meta?: {
    message?: string;
    [key: string]: unknown;
  };
};

export type IngestionQueuedResponse = {
  status: string;
  task_id: string;
  message?: string;
};

export type IngestionTaskResult = {
  status?: string;
  files_processed?: string[];
  total_pages_extracted?: number;
};

export type VectorDbWarmupResponse = {
  has_embeddings?: boolean;
  total_vector_count?: number;
};

export async function fetchEmbeddingStatus() {
  const response = await fetch(`${API_BASE_URL}/api/v1/ingest/warmup`, {
    method: "POST",
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error(
      `Vector status check failed with status ${response.status}`,
    );
  }

  const data = (await response.json()) as VectorDbWarmupResponse;
  return Boolean(data.has_embeddings);
}

export async function startIngestion(resetDb = false) {
  const response = await fetch(
    `${API_BASE_URL}/api/v1/ingest/run-ingestion?reset_db=${resetDb}`,
    { method: "POST" },
  );

  if (!response.ok) {
    throw new Error(`Training failed with status ${response.status}`);
  }

  const data = (await response.json()) as IngestionQueuedResponse;

  if (!data.task_id) {
    throw new Error("Training task was not created");
  }

  return data;
}

export async function fetchIngestionTaskStatus(taskId: string) {
  const response = await fetch(
    `${API_BASE_URL}/api/v1/ingest/ingestion-tasks/${taskId}`,
    { cache: "no-store" },
  );

  if (!response.ok) {
    throw new Error(`Task status failed with status ${response.status}`);
  }

  return (await response.json()) as CeleryTaskStatus<IngestionTaskResult>;
}
