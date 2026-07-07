-- MySQL 8.0 schema for the ZhihuRec V1 runtime boundary.
-- Raw ZhihuRec CSV files and build/demo_world artifacts remain offline inputs only.
-- Online services must read MySQL tables below as the single runtime source of truth.

CREATE DATABASE IF NOT EXISTS zhihurec_demo
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_unicode_ci;

USE zhihurec_demo;

DROP TABLE IF EXISTS user_event;
DROP TABLE IF EXISTS user_profile;
DROP TABLE IF EXISTS system_profile_seed;
DROP TABLE IF EXISTS hot_answer_snapshot;
DROP TABLE IF EXISTS query_topic_map;
DROP TABLE IF EXISTS answer_topic;
DROP TABLE IF EXISTS question_topic;
DROP TABLE IF EXISTS answer;
DROP TABLE IF EXISTS question;
DROP TABLE IF EXISTS app_user;
DROP TABLE IF EXISTS author;
DROP TABLE IF EXISTS topic;

CREATE TABLE topic (
  topic_id BIGINT NOT NULL,
  display_name VARCHAR(128) NULL COMMENT 'Synthetic/demo label because ZhihuRec does not expose raw topic text.',
  answer_count INT NOT NULL DEFAULT 0,
  question_count INT NOT NULL DEFAULT 0,
  source VARCHAR(32) NOT NULL DEFAULT 'zhihurec_1m',
  PRIMARY KEY (topic_id)
) ENGINE=InnoDB COMMENT='Project topic dimension derived from ZhihuRec.';

CREATE TABLE author (
  author_id BIGINT NOT NULL,
  display_name VARCHAR(128) NULL COMMENT 'Synthetic/demo author label.',
  is_excellent_author TINYINT(1) NOT NULL DEFAULT 0,
  follower_count INT NOT NULL DEFAULT 0,
  is_excellent_answerer TINYINT(1) NOT NULL DEFAULT 0,
  source VARCHAR(32) NOT NULL DEFAULT 'zhihurec_1m',
  PRIMARY KEY (author_id)
) ENGINE=InnoDB COMMENT='Content authors derived from ZhihuRec info_author.';

CREATE TABLE app_user (
  user_id BIGINT NOT NULL,
  display_name VARCHAR(128) NULL COMMENT 'Synthetic/demo user label.',
  register_ts BIGINT NULL,
  gender TINYINT NULL,
  login_frequency TINYINT NULL,
  follower_count INT NOT NULL DEFAULT 0,
  followed_topic_count INT NOT NULL DEFAULT 0,
  answer_count INT NOT NULL DEFAULT 0,
  question_count INT NOT NULL DEFAULT 0,
  comment_count INT NOT NULL DEFAULT 0,
  thanks_received_count INT NOT NULL DEFAULT 0,
  likes_received_count INT NOT NULL DEFAULT 0,
  province VARCHAR(64) NULL,
  city VARCHAR(64) NULL,
  followed_topic_ids_json JSON NULL,
  is_demo_user TINYINT(1) NOT NULL DEFAULT 0,
  source VARCHAR(32) NOT NULL DEFAULT 'zhihurec_1m',
  PRIMARY KEY (user_id)
) ENGINE=InnoDB COMMENT='Project users seeded from ZhihuRec info_user.';

CREATE TABLE question (
  question_id BIGINT NOT NULL,
  create_ts BIGINT NULL,
  answer_count INT NOT NULL DEFAULT 0,
  follower_count INT NOT NULL DEFAULT 0,
  invitation_count INT NOT NULL DEFAULT 0,
  comment_count INT NOT NULL DEFAULT 0,
  token_ids_json JSON NULL COMMENT 'Token IDs from ZhihuRec because raw text is unavailable.',
  topic_ids_json JSON NULL,
  display_title VARCHAR(255) NULL COMMENT 'Synthetic/demo title used by the UI.',
  source VARCHAR(32) NOT NULL DEFAULT 'zhihurec_1m',
  PRIMARY KEY (question_id)
) ENGINE=InnoDB COMMENT='Project question entities derived from ZhihuRec info_question.';

CREATE TABLE answer (
  answer_id BIGINT NOT NULL,
  question_id BIGINT NULL,
  author_id BIGINT NULL,
  is_anonymous TINYINT(1) NOT NULL DEFAULT 0,
  is_high_value TINYINT(1) NOT NULL DEFAULT 0,
  is_editor_recommended TINYINT(1) NOT NULL DEFAULT 0,
  create_ts BIGINT NULL,
  has_picture TINYINT(1) NOT NULL DEFAULT 0,
  has_video TINYINT(1) NOT NULL DEFAULT 0,
  thanks_count INT NOT NULL DEFAULT 0,
  likes_count INT NOT NULL DEFAULT 0,
  comment_count INT NOT NULL DEFAULT 0,
  collection_count INT NOT NULL DEFAULT 0,
  dislike_count INT NOT NULL DEFAULT 0,
  report_count INT NOT NULL DEFAULT 0,
  helpless_count INT NOT NULL DEFAULT 0,
  token_ids_json JSON NULL COMMENT 'Token IDs from ZhihuRec because raw answer text is unavailable.',
  topic_ids_json JSON NULL,
  display_summary TEXT NULL COMMENT 'Synthetic/demo summary used by the UI.',
  vector_key VARCHAR(128) NULL COMMENT 'Lookup key for ANN/vector assets built offline.',
  is_demo_selected TINYINT(1) NOT NULL DEFAULT 0,
  hot_score DOUBLE NOT NULL DEFAULT 0,
  click_count INT NOT NULL DEFAULT 0,
  impression_count INT NOT NULL DEFAULT 0,
  source VARCHAR(32) NOT NULL DEFAULT 'zhihurec_1m',
  PRIMARY KEY (answer_id),
  KEY idx_answer_question (question_id),
  KEY idx_answer_author (author_id),
  KEY idx_answer_hot_score (hot_score),
  CONSTRAINT fk_answer_question FOREIGN KEY (question_id) REFERENCES question (question_id),
  CONSTRAINT fk_answer_author FOREIGN KEY (author_id) REFERENCES author (author_id)
) ENGINE=InnoDB COMMENT='Main recommendation entity for the project.';

CREATE TABLE question_topic (
  question_id BIGINT NOT NULL,
  topic_id BIGINT NOT NULL,
  source_rank SMALLINT NOT NULL DEFAULT 0 COMMENT 'Position inside the original ZhihuRec topic list.',
  PRIMARY KEY (question_id, topic_id),
  KEY idx_question_topic_topic (topic_id),
  CONSTRAINT fk_question_topic_question FOREIGN KEY (question_id) REFERENCES question (question_id),
  CONSTRAINT fk_question_topic_topic FOREIGN KEY (topic_id) REFERENCES topic (topic_id)
) ENGINE=InnoDB COMMENT='Many-to-many bridge between questions and topics.';

CREATE TABLE answer_topic (
  answer_id BIGINT NOT NULL,
  topic_id BIGINT NOT NULL,
  source_rank SMALLINT NOT NULL DEFAULT 0 COMMENT 'Position inside the original ZhihuRec topic list.',
  PRIMARY KEY (answer_id, topic_id),
  KEY idx_answer_topic_topic (topic_id),
  CONSTRAINT fk_answer_topic_answer FOREIGN KEY (answer_id) REFERENCES answer (answer_id),
  CONSTRAINT fk_answer_topic_topic FOREIGN KEY (topic_id) REFERENCES topic (topic_id)
) ENGINE=InnoDB COMMENT='Many-to-many bridge between answers and topics.';

CREATE TABLE query_topic_map (
  query_key VARCHAR(512) NOT NULL COMMENT 'Normalized token-ID sequence or a synthetic demo alias.',
  display_query VARCHAR(255) NULL COMMENT 'Optional synthetic query string shown in the demo UI.',
  query_tokens_json JSON NULL,
  topic_id BIGINT NOT NULL,
  score DECIMAL(10, 6) NOT NULL COMMENT 'Offline co-occurrence score used for topic-aware recall boost.',
  evidence_query_count INT NOT NULL DEFAULT 0,
  evidence_user_count INT NOT NULL DEFAULT 0,
  match_rank INT NOT NULL DEFAULT 0,
  source_method VARCHAR(64) NOT NULL DEFAULT 'offline_user_topic_cooccurrence',
  PRIMARY KEY (query_key, topic_id),
  KEY idx_query_topic_topic (topic_id),
  KEY idx_query_topic_rank (query_key, match_rank),
  CONSTRAINT fk_query_topic_topic FOREIGN KEY (topic_id) REFERENCES topic (topic_id)
) ENGINE=InnoDB COMMENT='Offline query-to-topic bridge derived from ZhihuRec query and click behavior.';

CREATE TABLE hot_answer_snapshot (
  snapshot_key VARCHAR(64) NOT NULL COMMENT 'Named snapshot such as zhihurec_1m_v1.',
  rank_position INT NOT NULL,
  answer_id BIGINT NOT NULL,
  hot_score DOUBLE NOT NULL,
  click_count INT NOT NULL DEFAULT 0,
  impression_count INT NOT NULL DEFAULT 0,
  source_window VARCHAR(64) NOT NULL DEFAULT 'zhihurec_1m_full_window',
  PRIMARY KEY (snapshot_key, rank_position),
  UNIQUE KEY uq_hot_snapshot_answer (snapshot_key, answer_id),
  KEY idx_hot_answer_answer (answer_id),
  CONSTRAINT fk_hot_answer_snapshot_answer FOREIGN KEY (answer_id) REFERENCES answer (answer_id)
) ENGINE=InnoDB COMMENT='Fallback pool for hot answers in the v1 feed.';

CREATE TABLE system_profile_seed (
  seed_key VARCHAR(64) NOT NULL,
  topic_weights_json JSON NOT NULL,
  recent_clicked_answers_json JSON NULL,
  recent_queries_json JSON NULL,
  behavior_score DOUBLE NOT NULL DEFAULT 0,
  notes VARCHAR(255) NULL,
  PRIMARY KEY (seed_key)
) ENGINE=InnoDB COMMENT='Reusable cold-start or bootstrap profile seeds.';

CREATE TABLE user_profile (
  user_id BIGINT NOT NULL,
  cold_start_seed_key VARCHAR(64) NOT NULL DEFAULT 'cold_start_default',
  topic_weights_json JSON NOT NULL,
  recent_clicked_answers_json JSON NOT NULL,
  recent_queries_json JSON NOT NULL,
  behavior_score DOUBLE NOT NULL DEFAULT 0,
  user_vector_json JSON NULL COMMENT 'Optional compact vector summary used by retrieval services.',
  notes VARCHAR(255) NULL COMMENT 'Importer or debug note for the current seeded profile state.',
  last_event_ts BIGINT NULL,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (user_id),
  KEY idx_user_profile_seed (cold_start_seed_key),
  CONSTRAINT fk_user_profile_user FOREIGN KEY (user_id) REFERENCES app_user (user_id),
  CONSTRAINT fk_user_profile_seed FOREIGN KEY (cold_start_seed_key) REFERENCES system_profile_seed (seed_key)
) ENGINE=InnoDB COMMENT='Single-table v1 user profile storage.';

CREATE TABLE user_event (
  event_id BIGINT NOT NULL AUTO_INCREMENT,
  external_event_id VARCHAR(80) NULL COMMENT 'V2 idempotency key from Kafka/event producer.',
  user_id BIGINT NOT NULL,
  event_type ENUM(
    'search_query',
    'recommendation_click',
    'search_result_click',
    'feed_impression',
    'detail_view',
    'dwell',
    'upvote',
    'downvote',
    'share'
  ) NOT NULL,
  answer_id BIGINT NULL,
  query_key VARCHAR(512) NULL COMMENT 'Direct query key for search_query or matched_query_key carried by click events.',
  query_tokens_json JSON NULL,
  topic_ids_json JSON NULL COMMENT 'Topics used when updating the profile.',
  surface VARCHAR(32) NOT NULL DEFAULT 'feed',
  request_id VARCHAR(64) NULL,
  derived_from_raw TINYINT(1) NOT NULL DEFAULT 0,
  source_confidence ENUM('confirmed', 'heuristic', 'not_applicable') NOT NULL DEFAULT 'not_applicable',
  event_ts BIGINT NOT NULL,
  debug_payload_json JSON NULL,
  PRIMARY KEY (event_id),
  UNIQUE KEY uq_user_event_external_event_id (external_event_id),
  KEY idx_user_event_user_ts (user_id, event_ts),
  KEY idx_user_event_type_ts (event_type, event_ts),
  KEY idx_user_event_answer (answer_id),
  CONSTRAINT fk_user_event_user FOREIGN KEY (user_id) REFERENCES app_user (user_id),
  CONSTRAINT fk_user_event_answer FOREIGN KEY (answer_id) REFERENCES answer (answer_id)
) ENGINE=InnoDB COMMENT='Minimal v1 event log for closed-loop updates and replay.';
