import type { AskResponse, ChatMessage, SearchResponse, Video } from "@/types/api";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000/api";

async function json<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: init?.body instanceof FormData ? init.headers : { "Content-Type": "application/json", ...init?.headers }
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || response.statusText);
  }
  return response.json() as Promise<T>;
}

export function listVideos() {
  return json<Video[]>("/videos", { cache: "no-store" });
}

export function uploadVideos(files: File[]) {
  const body = new FormData();
  files.forEach((file) => body.append("files", file));
  return json<Video[]>("/videos/upload", { method: "POST", body });
}

export function addYoutubeVideos(urls: string[], resolution = 720) {
  return json<Video[]>("/videos/youtube", { method: "POST", body: JSON.stringify({ urls, resolution }) });
}

export function ask(question: string, videoIds: string[] = [], history: ChatMessage[] = []) {
  return json<AskResponse>("/ask", { method: "POST", body: JSON.stringify({ question, video_ids: videoIds, history }) });
}

export function search(query: string, videoIds: string[] = []) {
  return json<SearchResponse>("/search", { method: "POST", body: JSON.stringify({ query, video_ids: videoIds }) });
}

export function removeVideo(id: string) {
  return fetch(`${API_BASE}/videos/${id}`, { method: "DELETE" });
}

