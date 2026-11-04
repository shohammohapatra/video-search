"use client";

import { ChangeEvent, FormEvent, useEffect, useRef, useState } from "react";
import { AlertCircle, FileVideo, Link2, Loader2, Play, Plus, Search, Trash2, Upload } from "lucide-react";
import * as Dialog from "@radix-ui/react-dialog";

import { addYoutubeVideos, ask, listVideos, removeVideo, search, uploadVideos } from "@/lib/api";
import { formatTime } from "@/lib/time";
import type { AskResponse, ChatMessage, Source, Video } from "@/types/api";

type SavedChat = { id: string; title: string; messages: ChatMessage[]; videoIds: string[] };

export function VideoWorkbench() {
  const [videos, setVideos] = useState<Video[]>([]);
  const [selectedVideo, setSelectedVideo] = useState<Video | null>(null);
  const [selectedVideoIds, setSelectedVideoIds] = useState<string[]>([]);
  const [sources, setSources] = useState<Source[]>([]);
  const [answer, setAnswer] = useState<AskResponse | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [savedChats, setSavedChats] = useState<SavedChat[]>([]);
  const [currentChatId, setCurrentChatId] = useState<string | null>(null);
  const [libraryOpen, setLibraryOpen] = useState(true);
  const [historyOpen, setHistoryOpen] = useState(true);
  const [question, setQuestion] = useState("");
  const [isAsking, setIsAsking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const videoRef = useRef<HTMLVideoElement>(null);

  async function refresh() {
    const next = await listVideos();
    setVideos(next);
    setSelectedVideo((current) => current ?? next[0] ?? null);
    setSelectedVideoIds((current) => current.filter((id) => next.some((video) => video.id === id)));
  }

  useEffect(() => {
    refresh().catch((err) => setError(err.message));
    const timer = window.setInterval(() => refresh().catch(() => undefined), 5000);
    return () => window.clearInterval(timer);
  }, []);

  async function submitAsk(event: FormEvent) {
    event.preventDefault();
    if (!question.trim()) return;
    setIsAsking(true);
    setError(null);
    try {
      const currentQuestion = question.trim();
      const response = await ask(currentQuestion, selectedVideoIds, messages);
      setAnswer(response);
      setSources(response.sources);
      const nextMessages = [...messages, { role: "user" as const, content: currentQuestion }, { role: "assistant" as const, content: response.answer }];
      setMessages(nextMessages);
      const chatId = currentChatId ?? crypto.randomUUID();
      setCurrentChatId(chatId);
      setSavedChats((current) => {
        const title = nextMessages.find((message) => message.role === "user")?.content ?? "New chat";
        const existing = current.some((chat) => chat.id === chatId);
        return existing
          ? current.map((chat) => chat.id === chatId ? { ...chat, title, messages: nextMessages, videoIds: selectedVideoIds } : chat)
          : [{ id: chatId, title, messages: nextMessages, videoIds: selectedVideoIds }, ...current];
      });
      setQuestion("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to ask question");
    } finally {
      setIsAsking(false);
    }
  }

  function startNewChat() {
    const chatId = crypto.randomUUID();
    setCurrentChatId(chatId);
    setSavedChats((current) => [{ id: chatId, title: "New chat", messages: [], videoIds: selectedVideoIds }, ...current]);
    setMessages([]);
    setAnswer(null);
    setSources([]);
    setQuestion("");
    setError(null);
  }

  function deleteChat(chatId: string) {
    setSavedChats((current) => current.filter((chat) => chat.id !== chatId));
    if (currentChatId === chatId) {
      setCurrentChatId(null);
      setMessages([]);
      setAnswer(null);
      setSources([]);
    }
  }

  function openSavedChat(chat: SavedChat) {
    setCurrentChatId(chat.id);
    setMessages(chat.messages);
    setSelectedVideoIds(chat.videoIds);
    const lastAnswer = [...chat.messages].reverse().find((message) => message.role === "assistant");
    setAnswer(lastAnswer ? { answer: lastAnswer.content, grounded: true, sources: [] } : null);
    setSources([]);
  }

  async function submitSearch() {
    if (!question.trim()) return;
    setIsAsking(true);
    setError(null);
    try {
      const response = await search(question.trim(), selectedVideoIds);
      setAnswer(null);
      setSources(response.results);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to search videos");
    } finally {
      setIsAsking(false);
    }
  }

  async function deleteVideo(video: Video) {
    if (!window.confirm(`Remove "${video.title}" from the video library?`)) return;
    setError(null);
    try {
      await removeVideo(video.id);
      setVideos((current) => current.filter((item) => item.id !== video.id));
      setSelectedVideo((current) => (current?.id === video.id ? null : current));
      setSelectedVideoIds((current) => current.filter((id) => id !== video.id));
      setSources((current) => current.filter((source) => source.video_id !== video.id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to remove video");
    }
  }

  function watchSource(source: Source) {
    const video = videos.find((item) => item.id === source.video_id) ?? null;
    setSelectedVideo(video);
    if (source.youtube_url) {
      window.open(source.youtube_url, "_blank", "noopener,noreferrer");
      return;
    }
    window.setTimeout(() => {
      if (videoRef.current) {
        videoRef.current.currentTime = source.start_time;
        void videoRef.current.play();
      }
    }, 100);
  }

  function toggleVideoSelection(videoId: string) {
    setSelectedVideoIds((current) => current.includes(videoId)
      ? current.filter((id) => id !== videoId)
      : [...current, videoId]);
  }

  function selectAllVideos() {
    setSelectedVideoIds(videos.map((video) => video.id));
  }

  return (
    <div className="flex min-h-screen bg-[#f7f8fa] text-[#172033]">
      <aside className="hidden w-80 shrink-0 border-r border-slate-200 bg-white p-4 md:block">
        <div className="mb-4 flex items-center justify-between">
          <div>
            <h1 className="text-xl font-semibold">Grounded Search</h1>
          </div>
          <button type="button" onClick={startNewChat} className="rounded-md border border-slate-200 px-3 py-2 text-xs font-medium hover:bg-slate-50" title="Start a new chat">New chat</button>
          <Dialog.Root open={dialogOpen} onOpenChange={setDialogOpen}>
            <Dialog.Trigger className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-slate-200 bg-white hover:bg-slate-50" aria-label="Add videos">
              <Plus className="h-4 w-4" />
            </Dialog.Trigger>
            <AddVideosDialog onDone={() => { setDialogOpen(false); void refresh(); }} />
          </Dialog.Root>
        </div>
        <button type="button" onClick={() => setLibraryOpen((open) => !open)} className="mb-2 flex w-full items-center justify-between text-left text-xs font-medium uppercase tracking-wide text-slate-500">
          <span>Video Library</span><span>{libraryOpen ? "−" : "+"}</span>
        </button>
        {libraryOpen && <>
        <div className="mb-2 flex items-center justify-between text-xs text-slate-500">
          <span>{selectedVideoIds.length ? `${selectedVideoIds.length} video${selectedVideoIds.length === 1 ? "" : "s"} selected for search` : "All videos included in search"}</span>
          <button type="button" onClick={() => selectedVideoIds.length ? setSelectedVideoIds([]) : selectAllVideos()} className="font-medium text-slate-700 hover:text-slate-950">
            {selectedVideoIds.length ? "Search all videos" : "Select videos"}
          </button>
        </div>
        <div className="space-y-2">
          {videos.length === 0 ? (
            <div className="rounded-md border border-dashed border-slate-300 p-4 text-sm text-slate-500">Add uploads or YouTube URLs to begin indexing.</div>
          ) : (
            videos.map((video) => (
              <div
                key={video.id}
                className={`w-full rounded-md border p-3 text-left transition ${selectedVideo?.id === video.id ? "border-slate-900 bg-slate-50" : "border-slate-200 bg-white hover:bg-slate-50"}`}
              >
                <div className="flex items-start gap-3">
                  <input type="checkbox" checked={selectedVideoIds.includes(video.id)} onChange={() => toggleVideoSelection(video.id)} className="mt-1 h-4 w-4 accent-slate-900" aria-label={`Include ${video.title} in search`} />
                  <button type="button" onClick={() => setSelectedVideo(video)} className="flex min-w-0 flex-1 items-start gap-3 text-left" aria-label={`Select ${video.title}`}>
                  <FileVideo className="mt-1 h-4 w-4 text-slate-500" />
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium">{video.title}</p>
                    <p className="mt-1 text-xs text-slate-500">{video.source_type} · {video.status}</p>
                    {video.status !== "ready" && (
                      <div className="mt-2 h-1.5 rounded-full bg-slate-100">
                        <div className="h-1.5 rounded-full bg-slate-900" style={{ width: `${Math.round(video.progress * 100)}%` }} />
                      </div>
                    )}
                  </div>
                  </button>
                  <button type="button" onClick={() => void deleteVideo(video)} className="rounded-md p-1.5 text-slate-400 hover:bg-red-50 hover:text-red-600" aria-label={`Remove ${video.title}`} title="Remove video">
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
        </>}
        <button type="button" onClick={() => setHistoryOpen((open) => !open)} className="mt-5 flex w-full items-center justify-between border-t border-slate-200 pt-4 text-left text-xs font-medium uppercase tracking-wide text-slate-500">
          <span>Chat History</span><span>{historyOpen ? "−" : "+"}</span>
        </button>
        {historyOpen && <div className="mt-2 space-y-1">
          {savedChats.length === 0 ? <p className="text-xs text-slate-400">No previous chats</p> : savedChats.map((chat) => (
            <div key={chat.id} className="flex items-center gap-1 rounded-md hover:bg-slate-50">
              <button type="button" onClick={() => openSavedChat(chat)} className="min-w-0 flex-1 truncate px-2 py-2 text-left text-sm">{chat.title}</button>
              <button type="button" onClick={() => deleteChat(chat.id)} className="rounded-md p-1.5 text-slate-400 hover:bg-red-50 hover:text-red-600" aria-label={`Delete chat ${chat.title}`} title="Delete chat">
                <Trash2 className="h-3.5 w-3.5" />
              </button>
            </div>
          ))}
        </div>}
      </aside>

      <main className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center justify-between border-b border-slate-200 bg-white px-4 py-3 md:hidden">
          <h1 className="font-semibold">Grounded Search</h1>
          <Dialog.Root open={dialogOpen} onOpenChange={setDialogOpen}>
            <Dialog.Trigger className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-slate-200" aria-label="Add videos">
              <Plus className="h-4 w-4" />
            </Dialog.Trigger>
            <AddVideosDialog onDone={() => { setDialogOpen(false); void refresh(); }} />
          </Dialog.Root>
        </header>

        <section className="grid flex-1 gap-4 p-4 lg:grid-cols-[minmax(0,1fr)_420px]">
          <div className="space-y-4">
            <div className="overflow-hidden rounded-md border border-slate-200 bg-black">
              {selectedVideo?.source_type === "youtube" ? (
                <div className="flex aspect-video items-center justify-center px-6 text-center text-sm text-slate-200">
                  YouTube sources open at exact timestamps from source cards.
                </div>
              ) : selectedVideo ? (
                <video ref={videoRef} controls className="aspect-video w-full bg-black" src={`http://localhost:8000/api/videos/${selectedVideo.id}/stream`} />
              ) : (
                <div className="flex aspect-video items-center justify-center text-sm text-slate-300">Select or add a video</div>
              )}
            </div>

            <form onSubmit={submitAsk} className="rounded-md border border-slate-200 bg-white p-3">
              <div className="mb-2 flex items-center justify-between text-xs text-slate-500">
                <span>{selectedVideoIds.length ? `Searching in ${selectedVideoIds.length} selected video${selectedVideoIds.length === 1 ? "" : "s"}` : "Searching across all videos"}</span>
                {selectedVideoIds.length > 0 && <button type="button" onClick={() => setSelectedVideoIds([])} className="font-medium text-slate-700 hover:text-slate-950">Search all videos</button>}
              </div>
              <div className="flex gap-2">
                <input
                  value={question}
                  onChange={(event) => setQuestion(event.target.value)}
                  placeholder="Ask anything about your videos..."
                  className="min-w-0 flex-1 rounded-md border border-slate-200 px-3 py-2 outline-none focus:border-slate-900"
                />
                <button disabled={isAsking} className="inline-flex items-center gap-2 rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-60">
                  {isAsking ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
                  Ask
                </button>
                <button type="button" onClick={submitSearch} disabled={isAsking} className="inline-flex items-center gap-2 rounded-md border border-slate-200 px-3 py-2 text-sm font-medium hover:bg-slate-50 disabled:opacity-60" aria-label="Search">
                  <Search className="h-4 w-4" />
                </button>
              </div>
            </form>

            {error && <div className="flex items-center gap-2 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700"><AlertCircle className="h-4 w-4" />{error}</div>}

            <div className="rounded-md border border-slate-200 bg-white p-4">
              <p className="mb-2 text-sm font-semibold">AI Answer</p>
              {messages.length ? (
                <div className="space-y-3">
                  {messages.map((message, index) => (
                    <div key={`${message.role}-${index}`} className={message.role === "user" ? "text-sm font-medium text-slate-900" : "text-sm leading-6 text-slate-700"}>
                      {message.role === "user" ? `You: ${message.content}` : message.content}
                    </div>
                  ))}
                </div>
              ) : <p className="text-sm leading-6 text-slate-700">{answer?.answer ?? "Ask a question to get a grounded answer with timestamped sources."}</p>}
            </div>
          </div>

          <aside className="rounded-md border border-slate-200 bg-white p-4">
            <p className="mb-3 text-sm font-semibold">Sources</p>
            <div className="space-y-3">
              {sources.length === 0 ? (
                <p className="text-sm text-slate-500">Relevant segments will appear here.</p>
              ) : (
                sources.map((source) => (
                  <div key={`${source.video_id}-${source.start_time}`} className="rounded-md border border-slate-200 p-3">
                    <p className="text-sm font-medium">{source.video_title}</p>
                    <p className="mt-1 text-xs text-slate-500">{formatTime(source.start_time)} – {formatTime(source.end_time)} · score {source.score.toFixed(2)}</p>
                    <p className="mt-2 text-sm leading-5 text-slate-700">{source.excerpt}</p>
                    <button onClick={() => watchSource(source)} className="mt-3 inline-flex items-center gap-2 rounded-md border border-slate-200 px-3 py-1.5 text-sm font-medium hover:bg-slate-50">
                      <Play className="h-4 w-4" /> Watch at {formatTime(source.start_time)}
                    </button>
                  </div>
                ))
              )}
            </div>
          </aside>
        </section>
      </main>
    </div>
  );
}

function AddVideosDialog({ onDone }: { onDone: () => void }) {
  const [files, setFiles] = useState<File[]>([]);
  const [urls, setUrls] = useState("");
  const [resolution, setResolution] = useState(720);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function onFiles(event: ChangeEvent<HTMLInputElement>) {
    setFiles(Array.from(event.target.files ?? []));
  }

  async function process() {
    setBusy(true);
    setError(null);
    try {
      if (files.length) await uploadVideos(files);
      const cleanUrls = urls.split(/\s+/).map((url) => url.trim()).filter(Boolean);
      if (cleanUrls.length) await addYoutubeVideos(cleanUrls, resolution);
      onDone();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to add videos");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Dialog.Portal>
      <Dialog.Overlay className="fixed inset-0 bg-black/35" />
      <Dialog.Content className="fixed left-1/2 top-1/2 w-[min(92vw,640px)] -translate-x-1/2 -translate-y-1/2 rounded-md bg-white p-5 shadow-xl">
        <Dialog.Title className="text-lg font-semibold">Add Videos</Dialog.Title>
        <div className="mt-4 grid gap-4 md:grid-cols-2">
          <label className="flex min-h-44 cursor-pointer flex-col items-center justify-center rounded-md border border-dashed border-slate-300 p-4 text-center hover:bg-slate-50">
            <Upload className="mb-2 h-6 w-6 text-slate-500" />
            <span className="text-sm font-medium">Upload videos</span>
            <span className="mt-1 text-xs text-slate-500">mp4, mov, mkv, webm</span>
            <input type="file" multiple accept="video/mp4,video/quicktime,video/x-matroska,video/webm" onChange={onFiles} className="sr-only" />
            {files.length > 0 && <span className="mt-2 text-xs text-slate-700">{files.length} selected</span>}
          </label>
          <div className="rounded-md border border-slate-200 p-4">
            <div className="mb-2 flex items-center gap-2 text-sm font-medium"><Link2 className="h-4 w-4" /> YouTube URLs</div>
            <textarea value={urls} onChange={(event) => setUrls(event.target.value)} rows={7} placeholder="https://www.youtube.com/watch?v=..." className="w-full resize-none rounded-md border border-slate-200 p-2 text-sm outline-none focus:border-slate-900" />
            <label className="mt-3 block text-xs font-medium text-slate-600">
              Download resolution
              <select value={resolution} onChange={(event) => setResolution(Number(event.target.value))} className="mt-1 w-full rounded-md border border-slate-200 bg-white px-2 py-2 text-sm font-normal text-slate-800 outline-none focus:border-slate-900">
                <option value={360}>360p - faster processing</option>
                <option value={480}>480p - balanced</option>
                <option value={720}>720p - recommended</option>
                <option value={1080}>1080p - highest quality</option>
              </select>
            </label>
          </div>
        </div>
        {error && <p className="mt-3 text-sm text-red-700">{error}</p>}
        <div className="mt-5 flex justify-end gap-2">
          <Dialog.Close className="rounded-md border border-slate-200 px-4 py-2 text-sm font-medium hover:bg-slate-50">Cancel</Dialog.Close>
          <button onClick={process} disabled={busy || (!files.length && !urls.trim())} className="inline-flex items-center gap-2 rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-60">
            {busy && <Loader2 className="h-4 w-4 animate-spin" />} Process Videos
          </button>
        </div>
      </Dialog.Content>
    </Dialog.Portal>
  );
}
