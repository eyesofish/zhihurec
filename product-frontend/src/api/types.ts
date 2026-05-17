export interface TopicCard {
  topic_id: number;
  display_name: string;
}

export interface AuthorCard {
  author_id: number;
  display_name: string;
}

export interface ProfileTopicWeight {
  topic_id: number;
  weight: number;
}

export interface PersonaCard {
  user_id: number;
  display_name: string;
  behavior_score: number;
  top_topics: ProfileTopicWeight[];
}

export interface PersonaListResponse {
  items: PersonaCard[];
}

export interface SuggestionItem {
  query_key: string;
  label: string;
  topic_count: number;
}

export interface SuggestionListResponse {
  items: SuggestionItem[];
}

export interface AnswerCardResponse {
  answer_id: number;
  question_id: number;
  question_title: string;
  answer_summary: string;
  author: AuthorCard;
  topics: TopicCard[];
}

export interface FeedItemScores {
  base_recall_score: number;
  personalized_topic_score: number;
  default_topic_score: number;
  topic_match_score: number;
  query_recall_boost: number;
  final_score: number;
}

export interface FeedItem {
  answer_id: number;
  question_id: number;
  question_title: string;
  answer_summary: string;
  author: AuthorCard;
  topics: TopicCard[];
  selected_reason: string;
  scores: FeedItemScores;
  recall_sources: string[];
  is_fallback: boolean;
}

export interface FeedResponse {
  user_id: number;
  request_id: string;
  items: FeedItem[];
  debug?: unknown;
}

export interface SearchItemScores {
  topic_match_score: number;
  hot_backfill_score: number;
  final_score: number;
}

export interface SearchItem {
  answer_id: number;
  question_id: number;
  question_title: string;
  answer_summary: string;
  topics: TopicCard[];
  scores: SearchItemScores;
}

export interface SearchResponse {
  user_id: number;
  query_key: string;
  items: SearchItem[];
  debug?: unknown;
}

export interface ProfileRecentClick {
  answer_id: number;
  click_ts: number;
}

export interface ProfileRecentQuery {
  query_key: string;
  query_ts: number;
}

export interface DebugProfileResponse {
  user_id: number;
  cold_start_seed_key: string;
  behavior_score: number;
  topic_weights: ProfileTopicWeight[];
  recent_clicked_answers: ProfileRecentClick[];
  recent_queries: ProfileRecentQuery[];
}

export type EventTrackType =
  | "feed_impression"
  | "detail_view"
  | "dwell"
  | "upvote"
  | "downvote"
  | "share"
  | "recommendation_click"
  | "search_result_click";

export interface EventTrackRequest {
  user_id: number;
  event_type: EventTrackType;
  surface: string;
  answer_id?: number | null;
  query_key?: string | null;
  request_id?: string | null;
  dwell_ms?: number | null;
  debug?: boolean;
}

export interface EventTrackResponse {
  ok: boolean;
  event_type: EventTrackType;
  profile_updated: boolean;
  behavior_score: number | null;
}
