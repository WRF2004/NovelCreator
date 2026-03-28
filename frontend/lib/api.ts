export const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000/api";

type RequestOptions = RequestInit & { skipJson?: boolean };

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {})
    },
    cache: "no-store"
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `HTTP ${response.status}`);
  }
  if (options.skipJson) {
    return undefined as T;
  }
  return response.json() as Promise<T>;
}

export type APIBridgeConfig = {
  enabled: boolean;
  base_url?: string;
  api_key?: string;
  model?: string;
};

export type TrainingJob = {
  id: number;
  source_folder: string;
  base_model_path: string;
  dataset_output_dir: string;
  model_output_dir: string;
  status: string;
  progress: number;
  logs: string;
  error_message?: string | null;
  dataset_id?: number | null;
  model_id?: number | null;
  created_at: string;
  updated_at?: string | null;
};

export type DatasetRecord = {
  id: number;
  name: string;
  path: string;
  source_folder: string;
  samples: number;
  created_at: string;
};

export type LocalModelRecord = {
  id: number;
  name: string;
  path: string;
  base_model_path?: string | null;
  created_at: string;
};

export type Book = {
  id: number;
  title: string;
  description?: string | null;
  model_path?: string | null;
  created_at: string;
  updated_at?: string | null;
};

export type Chapter = {
  id: number;
  book_id: number;
  title: string;
  description?: string | null;
  content: string;
  file_path?: string | null;
  order_index: number;
  word_count: number;
  status: string;
  created_at: string;
  updated_at?: string | null;
};

export type GenerationResponse = {
  prompt: string;
  generated_text: string;
  used_model_path: string;
};

export async function startTraining(payload: Record<string, unknown>) {
  return request<TrainingJob>("/training/start", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function listTrainingJobs() {
  return request<TrainingJob[]>("/training/jobs");
}

export async function interruptTrainingJob(jobId: number) {
  return request<TrainingJob>(`/training/jobs/${jobId}/interrupt`, {
    method: "POST"
  });
}

export async function resumeTrainingJob(jobId: number) {
  return request<TrainingJob>(`/training/jobs/${jobId}/resume`, {
    method: "POST"
  });
}

export async function listDatasets() {
  return request<DatasetRecord[]>("/training/datasets");
}

export async function listModels() {
  return request<LocalModelRecord[]>("/training/models");
}

export async function listBooks() {
  return request<Book[]>("/books");
}

export async function createBook(payload: { title: string; description?: string; model_path?: string }) {
  return request<Book>("/books", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function updateBook(bookId: number, payload: Partial<Book>) {
  return request<Book>(`/books/${bookId}`, {
    method: "PATCH",
    body: JSON.stringify(payload)
  });
}

export async function getBook(bookId: number) {
  return request<Book>(`/books/${bookId}`);
}

export async function listChapters(bookId: number) {
  return request<Chapter[]>(`/books/${bookId}/chapters`);
}

export async function createChapter(bookId: number, payload: { title: string; description?: string; order_index?: number }) {
  return request<Chapter>(`/books/${bookId}/chapters`, {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function updateChapter(chapterId: number, payload: Partial<Chapter>) {
  return request<Chapter>(`/books/chapters/${chapterId}`, {
    method: "PATCH",
    body: JSON.stringify(payload)
  });
}

export async function generateChapter(payload: Record<string, unknown>) {
  return request<GenerationResponse>("/generation/chapter", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function generateStandalone(payload: Record<string, unknown>) {
  return request<GenerationResponse>("/generation/standalone", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}
