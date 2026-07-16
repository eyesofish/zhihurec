import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import PostCard from "./PostCard";
import type { FeedItem } from "../api/types";

const sponsoredItem: FeedItem = {
  answer_id: 301,
  question_id: 201,
  question_title: "Sponsored backend answer",
  answer_summary: "A sponsored answer summary.",
  author: { author_id: 101, display_name: "Author" },
  topics: [{ topic_id: 1, display_name: "Backend" }],
  selected_reason: "Sponsored candidate",
  scores: {
    base_recall_score: 0,
    personalized_topic_score: 0,
    default_topic_score: 0,
    topic_match_score: 0,
    query_recall_boost: 0,
    final_score: 225,
    sponsored_score: 225,
  },
  recall_sources: ["sponsored"],
  is_fallback: false,
  content_type: "sponsored",
  sponsored: {
    delivery_id: "ad-delivery-1",
    campaign_id: 9001,
    creative_id: 19001,
    label: "Sponsored",
  },
};

describe("PostCard", () => {
  it("visibly labels sponsored feed content", () => {
    render(
      <MemoryRouter>
        <PostCard item={sponsoredItem} userId={7248} />
      </MemoryRouter>,
    );

    expect(screen.getByText("Sponsored")).toBeInTheDocument();
  });
});
