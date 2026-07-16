import { useCallback, useEffect, useMemo, useState } from "react";
import { useLocation, useSearchParams } from "react-router-dom";
import { postSearch, stableClientId, trackEvent } from "../api/client";
import type { SearchItem } from "../api/types";
import { usePersona } from "../context/PersonaContext";
import PostCard from "../components/PostCard";
import SearchBox from "../components/SearchBox";

export default function SearchPage() {
  const { selectedPersona, bumpProfile } = usePersona();
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const rawQuery = searchParams.get("q") ?? "";
  const isExact = searchParams.get("exact") === "1";
  const [items, setItems] = useState<SearchItem[]>([]);
  const [resolvedQueryKey, setResolvedQueryKey] = useState<string>("");
  const [requestId, setRequestId] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const searchEventId = useMemo(
    () =>
      stableClientId(
        "search",
        `${location.key}:${selectedPersona?.user_id ?? "none"}:${rawQuery}:${isExact}`,
      ),
    [location.key, selectedPersona?.user_id, rawQuery, isExact],
  );

  useEffect(() => {
    if (!selectedPersona || !rawQuery) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    setItems([]);
    setResolvedQueryKey("");
    const input = isExact ? { queryKey: rawQuery } : { queryText: rawQuery };
    postSearch(selectedPersona.user_id, input, 10, searchEventId)
      .then((res) => {
        if (cancelled) return;
        setItems(res.items);
        setResolvedQueryKey(res.query_key);
        setRequestId(res.request_id);
        bumpProfile();
      })
      .catch((err: Error) => {
        if (cancelled) return;
        if (err.message.startsWith("422")) {
          setError("No matching query found. Try a suggested query.");
        } else {
          setError(err.message);
        }
      })
      .finally(() => {
        if (cancelled) return;
        setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [selectedPersona, rawQuery, isExact, bumpProfile, searchEventId]);

  const handleClick = useCallback(
    (answerId: number) => {
      if (!selectedPersona) return;
      trackEvent({
        event_id: `search-click-${requestId}:${answerId}`,
        user_id: selectedPersona.user_id,
        event_type: "search_result_click",
        surface: "search",
        answer_id: answerId,
        query_key: resolvedQueryKey || rawQuery,
        request_id: requestId || searchEventId,
      }).then(() => bumpProfile());
    },
    [selectedPersona, resolvedQueryKey, rawQuery, requestId, searchEventId, bumpProfile],
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
        <SearchBox initialQuery={rawQuery} />
      </div>

      {rawQuery && (
        <div style={{ fontSize: 13, color: "var(--zr-text-muted)", marginBottom: 12 }}>
          Results for <strong>{rawQuery}</strong>
        </div>
      )}

      {loading && <div className="zr-status">Searching...</div>}
      {error && <div className="zr-status">Search failed: {error}</div>}

      {!loading && !error && rawQuery && items.length === 0 && (
        <div className="zr-status">No results for "{rawQuery}".</div>
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
