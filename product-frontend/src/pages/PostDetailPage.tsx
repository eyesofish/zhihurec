import { ArrowLeft } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { getAnswerCard, trackEvent } from "../api/client";
import type { AnswerCardResponse } from "../api/types";
import { usePersona } from "../context/PersonaContext";

export default function PostDetailPage() {
  const { answerId: answerIdParam } = useParams<{ answerId: string }>();
  const answerId = Number(answerIdParam);
  const { selectedPersona, bumpProfile } = usePersona();
  const [data, setData] = useState<AnswerCardResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!answerId || isNaN(answerId)) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    getAnswerCard(answerId)
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
  }, [answerId]);

  useEffect(() => {
    if (!data || !selectedPersona) return;
    trackEvent({
      user_id: selectedPersona.user_id,
      event_type: "detail_view",
      surface: "post_detail",
      answer_id: data.answer_id,
    }).then(() => bumpProfile());
  }, [data, selectedPersona, bumpProfile]);

  if (isNaN(answerId)) {
    return (
      <main className="zr-center">
        <div className="zr-status">Invalid post ID.</div>
      </main>
    );
  }

  if (loading) {
    return (
      <main className="zr-center">
        <div className="zr-status">Loading post...</div>
      </main>
    );
  }

  if (error) {
    return (
      <main className="zr-center">
        <div className="zr-status">Failed to load post: {error}</div>
      </main>
    );
  }

  if (!data) {
    return (
      <main className="zr-center">
        <div className="zr-status">Post not found.</div>
      </main>
    );
  }

  const mainTopic = data.topics?.[0];

  return (
    <main className="zr-center">
      <div className="zr-post-detail">
        <Link to="/" className="zr-back-link">
          <ArrowLeft size={14} />
          Back to feed
        </Link>

        <div className="zr-card__meta">
          {mainTopic && (
            <span className="zr-card__community">
              <span
                className="zr-card__avatar"
                style={{
                  background: `linear-gradient(135deg, hsl(${mainTopic.topic_id * 47 % 360}, 60%, 55%), hsl(${mainTopic.topic_id * 83 % 360}, 70%, 65%))`,
                }}
              />
              r/topic-{mainTopic.topic_id}
            </span>
          )}
          <span>Posted by u/user-{data.author.author_id}</span>
        </div>

        <h1 className="zr-post-detail__title">{data.question_title}</h1>

        {data.topics.length > 0 && (
          <div className="zr-card__chips">
            {data.topics.map((t) => (
              <span key={t.topic_id} className="zr-chip">
                {t.display_name}
              </span>
            ))}
          </div>
        )}

        <div className="zr-post-detail__summary">{data.answer_summary}</div>
      </div>
    </main>
  );
}
