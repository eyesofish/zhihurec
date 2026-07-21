import type {
  ArticleCardResponse,
  DebugProfileResponse,
  EventTrackRequest,
  EventTrackResponse,
  FeedResponse,
  PersonaListResponse,
  SearchResponse,
  SuggestionListResponse,
} from "./types";

const BASE_URL: string =
  (import.meta.env.VITE_NEWSREC_API_BASE as string | undefined)?.trim() ||
  "http://127.0.0.1:8000";

export function newClientId(prefix: string): string {
  const randomPart =
    globalThis.crypto?.randomUUID?.() ??
    `${Date.now().toString(36)}-${Math.random().toString(36).slice(2)}`;
  return `${prefix}-${randomPart}`;
}

const stableClientIds = new Map<string, string>();

export function stableClientId(prefix: string, logicalKey: string): string {
  const cacheKey = `${prefix}:${logicalKey}`;
  const existing = stableClientIds.get(cacheKey);
  if (existing) return existing;
  const created = newClientId(prefix);
  stableClientIds.set(cacheKey, created);
  return created;
}

async function request<T>(
  path: string,
  init?: RequestInit & { params?: Record<string, string | number | boolean | undefined> },
): Promise<T> {
  const url = new URL(path, BASE_URL);
  if (init?.params) {
    for (const [key, value] of Object.entries(init.params)) {
      if (value === undefined || value === null) continue;
      url.searchParams.set(key, String(value));
    }
  }
  const { params: _params, ...rest } = init ?? {};
  const response = await fetch(url.toString(), {
    headers: { "Content-Type": "application/json" },
    ...rest,
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(`${response.status} ${response.statusText}: ${text}`);
  }
  return (await response.json()) as T;
}

export function listPersonas(limit = 10): Promise<PersonaListResponse> {
  return request<PersonaListResponse>("/personas", { params: { limit } });
}

export function listSearchSuggestions(limit = 12): Promise<SuggestionListResponse> {
  return request<SuggestionListResponse>("/search/suggestions", { params: { limit } });
}

export function getFeed(
  userId: number,
  pageSize = 10,
  debug = false,
  requestId?: string,
): Promise<FeedResponse> {
  return request<FeedResponse>("/feed", {
    params: { user_id: userId, page_size: pageSize, debug, request_id: requestId },
  });
}

export interface SearchInput {
  queryText?: string;
  queryKey?: string;
}

export function postSearch(
  userId: number,
  input: SearchInput,
  pageSize = 10,
  eventId?: string,
): Promise<SearchResponse> {
  return request<SearchResponse>("/search", {
    method: "POST",
    body: JSON.stringify({
      user_id: userId,
      event_id: eventId,
      query_text: input.queryText,
      query_key: input.queryKey,
      page_size: pageSize,
    }),
  });
}

export function getArticleCard(articleId: number): Promise<ArticleCardResponse> {
  return request<ArticleCardResponse>(`/articles/${articleId}`);
}

export function getDebugProfile(userId: number): Promise<DebugProfileResponse> {
  return request<DebugProfileResponse>("/debug/profile", { params: { user_id: userId } });
}

export function trackEvent(payload: EventTrackRequest): Promise<EventTrackResponse> {
  return request<EventTrackResponse>("/event/track", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
