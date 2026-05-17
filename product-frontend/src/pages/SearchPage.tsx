import { useCallback, useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { postSearch, trackEvent } from "../api/client";
import type { SearchItem } from "../api/types";
import { usePersona } from "../context/PersonaContext";
import PostCard from "../components/PostCard";
import SearchBox from "../components/SearchBox";

export default function SearchPage() {
  const { selectedPersona, bumpProfile } = usePersona();
  const [searchParams] = useSearchParams();
  const queryKey = searchParams.get("q") ?? "";
  const [items, setItems] = useState<SearchItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!selectedPersona || !queryKey) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    setItems([]);
    postSearch(selectedPersona.user_id, queryKey, 10)
      .then((res) => {
        if (cancelled) return;
        setItems(res.items);
        bumpProfile();
      })
      .catch((err: Error) => {
        if (cancelled) return;
        setError(err.message);
      })
      .finally(() => {
        if (cancelled) return;
        setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [selectedPersona, queryKey, bumpProfile]);

  const handleClick = useCallback(
    (answerId: number) => {
      if (!selectedPersona) return;
      trackEvent({
        user_id: selectedPersona.user_id,
        event_type: "search_result_click",
        surface: "search",
        answer_id: answerId,
        query_key: queryKey,
      }).then(() => bumpProfile());
    },
    [selectedPersona, queryKey, bumpProfile],
  );

  if (!selectedPersona) {
    return (
      <main className="zr-center">
        <div className="zr-status">Select a persona to search.</div>
      </main>
    );
  }

  return (
    <main className="zr-center">
      <div style={{ marginBottom: 16 }}>
        <SearchBox initialQuery={queryKey} />
      </div>

      {queryKey && (
        <div style={{ fontSize: 13, color: "var(--zr-text-muted)", marginBottom: 12 }}>
          Results for <strong>{queryKey}</strong>
        </div>
      )}

      {loading && <div className="zr-status">Searching...</div>}
      {error && <div className="zr-status">Search failed: {error}</div>}

      {!loading && !error && queryKey && items.length === 0 && (
        <div className="zr-status">No results for "{queryKey}".</div>
      )}

      {items.map((item) => (
        <PostCard
          key={item.answer_id}
          item={item}
          userId={selectedPersona.user_id}
          surface="search"
          onTrackClick={() => handleClick(item.answer_id)}
          onProfileChanged={bumpProfile}
        />
      ))}
    </main>
  );
}
