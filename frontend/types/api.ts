export type VideoStatus = "pending" | "downloading" | "processing" | "ready" | "failed";
export type SourceType = "upload" | "youtube";

export interface Video {
  id: string;
  title: string;
  source_type: SourceType;
  source_url: string | null;
  thumbnail_path: string | null;
  duration: number | null;
  status: VideoStatus;
  progress: number;
  processing_error: string | null;
  created_at: string;
  updated_at: string;
}

export interface Source {
  video_id: string;
  video_title: string;
  start_time: number;
  end_time: number;
  score: number;
  excerpt: string;
  youtube_url: string | null;
}

export interface AskResponse {
  answer: string;
  grounded: boolean;
  sources: Source[];
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export interface SearchResponse {
  results: Source[];
}

