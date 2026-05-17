import { useCallback, useEffect, useRef, useState } from "react";
import { getFeed, trackEvent } from "../api/client";
import type { FeedItem } from "../api/types";
import { usePersona } from "../context/PersonaContext";
import PostCard from "../components/PostCard";

export default function FeedPage() {
  const { selectedPersona, refreshTick, bumpProfile } = usePersona();
  const [items, setItems] = useState<FeedItem[]>([]);
  const [requestId, setRequestId] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sort, setSort] = useState<"best" | "hot" | "new">("best");
  const trackedRef = useRef<Set<number>>(new Set());

  useEffect(() => {
    if (!selectedPersona) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    getFeed(selectedPersona.user_id, 10, true)
      .then((res) => {
        if (cancelled) return;
        setItems(res.items);
        setRequestId(res.request_id);
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
  }, [selectedPersona, refreshTick]);

  useEffect(() => {
    if (!selectedPersona || !requestId || items.length === 0) return;
    const newIds = items.map((i) => i.answer_id).filter((id) => !trackedRef.current.has(id));
    if (newIds.length === 0) return;
    newIds.forEach((id) => trackedRef.current.add(id));
    trackEvent({
      user_id: selectedPersona.user_id,
      event_type: "feed_impression",
      surface: "feed",
      request_id: requestId,
    });
  }, [selectedPersona, requestId, items]);

  const handleClick = useCallback(
    (answerId: number) => {
      if (!selectedPersona) return;
      trackEvent({
        user_id: selectedPersona.user_id,
        event_type: "recommendation_click",
        surface: "feed",
        answer_id: answerId,
        request_id: requestId,
      }).then(() => bumpProfile());
    },
    [selectedPersona, requestId, bumpProfile],
  );

  if (!selectedPersona) {
    return <div className="zr-status">Select a persona to see your feed.</div>;
  }
  if (error) {
    return <div className="zr-status">Failed to load feed: {error}</div>;
  }

  return (
    <main className="zr-center">
      <div className="zr-sort-tabs">
        {(["best", "hot", "new"] as const).map((s) => (
          <button
            key={s}
            className={`zr-sort-tab${sort === s ? " zr-sort-tab--active" : ""}`}
            onClick={() => setSort(s)}
          >
            {s.charAt(0).toUpperCase() + s.slice(1)}
          </button>
        ))}
      </div>

      {loading && items.length === 0 && <div className="zr-status">Loading feed...</div>}

      {!loading && items.length === 0 && (
        <div className="zr-status">No posts in feed. Try selecting a different persona.</div>
      )}

      {items.map((item) => (
        <PostCard
          key={item.answer_id}
          item={item}
          userId={selectedPersona.user_id}
          requestId={requestId}
          showReason
          onTrackClick={() => handleClick(item.answer_id)}
          onProfileChanged={bumpProfile}
        />
      ))}
    </main>
  );
}
