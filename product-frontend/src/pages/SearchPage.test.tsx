import { StrictMode } from "react";
import { render, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import SearchPage from "./SearchPage";
import { postSearch } from "../api/client";

const bumpProfile = vi.fn();
const selectedPersona = {
  user_id: 7248,
  display_name: "Backend Explorer",
  behavior_score: 0,
  top_topics: [],
};

vi.mock("../context/PersonaContext", () => ({
  usePersona: () => ({
    selectedPersona,
    bumpProfile,
  }),
}));

vi.mock("react-router-dom", async (importOriginal) => {
  const actual = await importOriginal<typeof import("react-router-dom")>();
  return {
    ...actual,
    useLocation: () => ({ key: "search-route" }),
    useSearchParams: () => [new URLSearchParams("q=backend")],
  };
});

vi.mock("../api/client", () => ({
  postSearch: vi.fn(),
  stableClientId: vi.fn(() => "search-event-stable"),
  trackEvent: vi.fn(),
}));

vi.mock("../components/PostCard", () => ({
  default: () => <div>post</div>,
}));

vi.mock("../components/SearchBox", () => ({
  default: () => <div>search box</div>,
}));

describe("SearchPage idempotency", () => {
  beforeEach(() => {
    vi.mocked(postSearch).mockResolvedValue({
      user_id: 7248,
      request_id: "search-event-stable",
      query_key: "10 11",
      items: [],
    });
  });

  it("reuses one event ID across StrictMode effect retries", async () => {
    render(
      <StrictMode>
        <SearchPage />
      </StrictMode>,
    );

    await waitFor(() => expect(postSearch).toHaveBeenCalled());
    expect(
      new Set(vi.mocked(postSearch).mock.calls.map((call) => call[3])),
    ).toEqual(new Set(["search-event-stable"]));
  });
});
