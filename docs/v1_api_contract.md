# V1 API Contract

## Purpose
This document defines the minimal online API surface for the ZhihuRec-based closed-loop project.

The contract sits on top of project-owned tables and offline-built assets, not on top of the raw ZhihuRec CSV files directly.

Primary storage boundary:
- relational tables in [v1_schema.sql](/D:/Github/zhihurec/sql/v1_schema.sql)
- offline-derived bridge assets from [build_demo_world.py](/D:/Github/zhihurec/scripts/build_demo_world.py)

Important raw-data limitation:
- ZhihuRec does not expose raw question text, answer text, author names, or topic names.
- Therefore `display_title`, `display_summary`, `display_name`, and `display_query` are synthetic demo fields built offline.
- The internal semantic keys remain `answer_id`, `question_id`, `topic_id`, and `query_key`.

## Runtime Data Flow
`raw ZhihuRec CSVs`
-> `scripts/build_demo_world.py`
-> `answer/question/author/topic/query_topic_map/hot_answer_snapshot/user_profile seeds`
-> `MySQL tables`
-> `feed/search/event/profile APIs`

## Endpoint Overview
- `GET /feed`
- `POST /search`
- `POST /event/recommendation_click`
- `POST /event/search_result_click`
- `GET /debug/profile`

## 1. `GET /feed`

### Purpose
Return the top answer cards for one demo user after combining:
- dual-tower-style base recall or a future vector retrieval layer
- topic-weight profile adjustment
- recent-query topic boost
- hot fallback if the main recall pool is too small

### Request
Query params:
- `user_id` required
- `page_size` optional, default `10`
- `debug` optional, default `false`

Example:
```http
GET /feed?user_id=123&page_size=10&debug=true
```

### Main storage touchpoints
- `user_profile`
- `answer`
- `question`
- `author`
- `topic`
- `answer_topic`
- `hot_answer_snapshot`
- future vector assets referenced by `answer.vector_key`

### Response
```json
{
  "user_id": 123,
  "request_id": "feed-20260417-001",
  "items": [
    {
      "answer_id": 456,
      "question_id": 321,
      "question_title": "Question 321",
      "answer_summary": "Synthetic answer summary for answer 456.",
      "author": {
        "author_id": 9001,
        "display_name": "Author 9001"
      },
      "topics": [
        {"topic_id": 12, "display_name": "Topic 12"}
      ],
      "selected_reason": "Selected because topic match and recent-query boost aligned.",
      "scores": {
        "base_recall_score": 0.812,
        "personalized_topic_score": 0.161,
        "default_topic_score": 0.029,
        "topic_match_score": 0.174,
        "query_recall_boost": 0.091,
        "final_score": 1.077
      },
      "recall_sources": ["dual_tower"],
      "is_fallback": false
    }
  ],
  "debug": {
    "profile_summary": {
      "behavior_score": 19.0,
      "top_topics": [
        {"topic_id": 12, "weight": 0.32}
      ]
    },
    "recall_candidates": [
      {
        "answer_id": 456,
        "source": "dual_tower",
        "base_recall_score": 0.812
      }
    ],
    "fallback_used": false,
    "cold_start_mix": {
      "alpha": 0.885443,
      "behavior_score": 365.0,
      "default_seed_key": "cold_start_default",
      "default_topic_count": 10
    }
  }
}
```

### Notes
- `items` should come from derived content tables, not directly from `data/zhihurec_1m/raw/*.csv`.
- `question_title`, `answer_summary`, and `display_name` may remain synthetic in v1.

## 2. `POST /search`

### Purpose
Record a search intent signal and return a minimal answer result list through `query -> topic -> answer`.

### Request
```json
{
  "user_id": 123,
  "query_key": "8481 8482",
  "query_text": "Query 8481 8482",
  "page_size": 10,
  "debug": true
}
```

### Main storage touchpoints
- `query_topic_map`
- `answer`
- `question`
- `author`
- `topic`
- `answer_topic`
- `user_profile` for writing `recent_queries`
- `user_event` for `search_query`

### Behavior
- write a `search_query` event
- append the query to `user_profile.recent_queries`
- look up related topics from `query_topic_map`
- retrieve matching answers via topic relationships
- return top results

### Response
```json
{
  "user_id": 123,
  "query_key": "8481 8482",
  "items": [
    {
      "answer_id": 456,
      "question_id": 321,
      "question_title": "Question 321",
      "answer_summary": "Synthetic answer summary for answer 456.",
      "topics": [
        {"topic_id": 12, "display_name": "Topic 12"}
      ],
      "scores": {
        "topic_match_score": 0.81,
        "hot_backfill_score": 0.00,
        "final_score": 0.81
      }
    }
  ],
  "debug": {
    "matched_topics": [
      {"topic_id": 12, "score": 0.81, "rank": 1}
    ],
    "result_sources": [
      {"answer_id": 456, "source": "topic_lookup"}
    ]
  }
}
```

### Notes
- `query_key` is the internal semantic key in v1.
- `query_text` is optional display copy and may be synthetic.

## 3. `POST /event/recommendation_click`

### Purpose
Write a feed-click event and update the user profile with answer topics.

### Request
```json
{
  "user_id": 123,
  "answer_id": 456,
  "request_id": "feed-20260417-001",
  "debug": true
}
```

### Main storage touchpoints
- `user_event`
- `answer`
- `answer_topic`
- `user_profile`

### Response
```json
{
  "ok": true,
  "event_type": "recommendation_click",
  "debug": {
    "updated_topics": [
      {"topic_id": 12, "delta": 0.08}
    ],
    "recent_clicked_answers_tail": [
      {"answer_id": 456, "click_ts": 1713399999}
    ],
    "behavior_score": 22.0
  }
}
```

## 4. `POST /event/search_result_click`

### Purpose
Write a stronger confirmation event after search and update the profile with:
- query-matched topics
- answer-carried topics
- stronger overlap contribution where both sets intersect

### Request
```json
{
  "user_id": 123,
  "answer_id": 456,
  "query_key": "8481 8482",
  "request_id": "search-20260417-001",
  "debug": true
}
```

### Main storage touchpoints
- `user_event`
- `query_topic_map`
- `answer_topic`
- `user_profile`

### Response
```json
{
  "ok": true,
  "event_type": "search_result_click",
  "debug": {
    "query_topics": [
      {"topic_id": 12, "score": 0.81}
    ],
    "answer_topics": [
      {"topic_id": 12}
    ],
    "overlap_topics": [
      {"topic_id": 12, "boost_type": "strong_confirm"}
    ],
    "behavior_score": 27.0
  }
}
```

## 5. `GET /debug/profile`

### Purpose
Expose the current v1 profile state for debugging and interviews.

### Request
Query params:
- `user_id` required

### Main storage touchpoints
- `user_profile`
- `system_profile_seed`
- optionally recent `user_event`

### Response
```json
{
  "user_id": 123,
  "cold_start_seed_key": "cold_start_default",
  "behavior_score": 27.0,
  "topic_weights": [
    {"topic_id": 12, "weight": 0.32}
  ],
  "recent_clicked_answers": [
    {"answer_id": 456, "click_ts": 1713399999}
  ],
  "recent_queries": [
    {"query_key": "8481 8482", "query_ts": 1713399900}
  ],
  "vector_summary": {
    "vector_key_count": 10,
    "top_contributing_topics": [
      {"topic_id": 12, "weight": 0.32}
    ]
  }
}
```

## Verification Checklist
- `GET /feed` must read project-owned answers and profile state, not raw CSV rows.
- `POST /search` must persist `search_query` intent and read `query_topic_map`.
- Click endpoints must update `user_profile` and write `user_event`.
- `GET /debug/profile` must expose the profile that the recommender actually uses.
