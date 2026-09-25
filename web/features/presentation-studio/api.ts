import { API_BASE_URL } from "@/lib/api";

export type Element = { target: string; text: string; kind: string; name: string; font_size: number; width: number; height: number; x: number; y: number };
export type Slide = { number: number; title: string; elements: Element[]; width: number; height: number };
export type Revision = { id: number; number: number; label: string; slide_count: number; created_at: string; slides?: Slide[] };
export type Reference = { id: string; kind: string; name: string; locator: string; enabled: boolean; text_length: number; excerpt: string; updated_at: string; metadata: { image?: boolean; vision_pending?: boolean; empty?: boolean; truncated?: boolean; files?: string[]; omitted_files?: number } };
export type Plan = { message?: string; questions?: string[]; image_requests?: string[]; changes?: { slide: number; edits: { target: string; text: string }[] }[]; additions?: { template_slide: number; title: string; brief: string }[]; rewrite_slides?: number[]; base_revision?: number; sources?: { id: string; name: string }[]; omitted_reference_count?: number };
export type Message = { id: number; role: string; content: string; plan: Plan; applied_revision: number | null };
export type Job = { id: string; kind: string; status: string; progress: string; error: string; updated_at: string };
export type Project = { id: string; title: string; instruction: string; audience: string; template_confirmed: boolean; protected_slides: number[]; archived: boolean; current: Revision; updated_at: string; references?: Reference[]; revisions?: Revision[]; messages?: Message[]; jobs?: Job[] };
export type PersonalTemplate = { id: string; name: string; slide_count: number; protected_slides: number[] };
export type Capabilities = { model: string; local_paths_allowed: boolean; path_note: string };
const base = `${API_BASE_URL}/api/presentation-studio/`;

export function auth() {
  const token = localStorage.getItem("auth_token");
  if (!token) throw new Error("로그인 후 발표자료 작업실을 이용해 주세요.");
  return { Authorization: `Token ${token}` };
}

export async function api<T>(path: string, method = "GET", data?: object | FormData): Promise<T> {
  const form = data instanceof FormData;
  const response = await fetch(base + path, { method, headers: { ...auth(), ...(!form && data ? { "Content-Type": "application/json" } : {}) }, body: data ? (form ? data : JSON.stringify(data)) : undefined });
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || "요청을 처리하지 못했습니다.");
  return result as T;
}

export async function download(path: string, filename: string) {
  const response = await fetch(base + path, { headers: auth() });
  if (!response.ok) throw new Error("다운로드에 실패했습니다.");
  const url = URL.createObjectURL(await response.blob());
  const a = document.createElement("a"); a.href = url; a.download = filename; a.click();
  setTimeout(() => URL.revokeObjectURL(url), 3000);
}

export const previewURL = (project: string, revision: number, page: number) => `${base}projects/${project}/revisions/${revision}/pages/${page}/`;
