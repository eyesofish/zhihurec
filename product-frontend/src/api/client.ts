import type {
  AnswerCardResponse,
  DebugProfileResponse,
  EventTrackRequest,
  EventTrackResponse,
  FeedResponse,
  PersonaListResponse,
  SearchResponse,
  SuggestionListResponse,
} from "./types";

const BASE_URL: string =
  (import.meta.env.VITE_ZHIHUREC_API_BASE as string | undefined)?.trim() ||
  "http://127.0.0.1:8000";

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

export function getFeed(userId: number, pageSize = 10, debug = false): Promise<FeedResponse> {
  return request<FeedResponse>("/feed", {
    params: { user_id: userId, page_size: pageSize, debug },
  });
}

export function postSearch(
  userId: number,
  queryKey: string,
  pageSize = 10,
): Promise<SearchResponse> {
  return request<SearchResponse>("/search", {
    method: "POST",
    body: JSON.stringify({ user_id: userId, query_key: queryKey, page_size: pageSize }),
  });
}

export function getAnswerCard(answerId: number): Promise<AnswerCardResponse> {
  return request<AnswerCardResponse>(`/answers/${answerId}`);
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
