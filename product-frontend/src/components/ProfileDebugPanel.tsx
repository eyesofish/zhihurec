import { useEffect, useState } from "react";
import { getDebugProfile } from "../api/client";
import type { DebugProfileResponse } from "../api/types";
import TopicWeightChart from "./TopicWeightChart";

interface Props {
  userId: number;
  refreshTick: number;
}

export default function ProfileDebugPanel({ userId, refreshTick }: Props) {
  const [data, setData] = useState<DebugProfileResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    getDebugProfile(userId)
      .then((res) => {
        if (cancelled) return;
        setData(res);
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
  }, [userId, refreshTick]);

  if (loading && !data) {
    return <div className="zr-status">Loading profile...</div>;
  }
  if (error) {
    return <div className="zr-status">Profile: {error}</div>;
  }
  if (!data) return null;

  const sortedWeights = [...data.topic_weights].sort((a, b) => b.weight - a.weight);

  return (
    <div className="zr-rail-card">
      <div className="zr-rail-card__title">Profile Debug</div>
      <div className="zr-profile-debug__row">
        <span>Behavior</span>
        <span className="zr-profile-debug__weight">{data.behavior_score.toFixed(1)}</span>
      </div>
      <div className="zr-profile-debug__row zr-profile-debug__row--muted">
        <span>Cold start</span>
        <span>{data.cold_start_seed_key}</span>
      </div>
      <div className="zr-profile-debug__row zr-profile-debug__row--muted">
        <span>Vector keys</span>
        <span>{data.vector_summary?.vector_key_count ?? sortedWeights.length}</span>
      </div>

      <div style={{ marginTop: 8 }}>
        <div className="zr-profile-debug__row zr-profile-debug__row--muted" style={{ fontWeight: 600 }}>
          <span>Topic Weights</span>
        </div>
        <TopicWeightChart topicWeights={sortedWeights} />
        {sortedWeights.slice(0, 8).map((tw) => (
          <div key={tw.topic_id} className="zr-profile-debug__row">
            <span>Topic {tw.topic_id}</span>
            <span className="zr-profile-debug__weight">{tw.weight.toFixed(2)}</span>
          </div>
        ))}
        {sortedWeights.length === 0 && (
          <div className="zr-profile-debug__row zr-profile-debug__row--muted">No weights yet</div>
        )}
      </div>

      {data.recent_clicked_answers.length > 0 && (
        <div style={{ marginTop: 8 }}>
          <div className="zr-profile-debug__row zr-profile-debug__row--muted" style={{ fontWeight: 600 }}>
            <span>Recent Clicks</span>
          </div>
          {data.recent_clicked_answers.slice(0, 5).map((rc, i) => (
            <div key={`${rc.answer_id}-${i}`} className="zr-profile-debug__row zr-profile-debug__row--muted">
              <span>Answer {rc.answer_id}</span>
              <span>{new Date(rc.click_ts * 1000).toLocaleDateString()}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
