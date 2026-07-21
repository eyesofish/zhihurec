import { ArrowLeft } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { getArticleCard, trackEvent } from "../api/client";
import type { ArticleCardResponse } from "../api/types";
import { usePersona } from "../context/PersonaContext";

export default function ArticleDetailPage() {
  const { articleId: articleIdParam } = useParams<{ articleId: string }>();
  const articleId = Number(articleIdParam);
  const { selectedPersona, bumpProfile } = usePersona();
  const [data, setData] = useState<ArticleCardResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!articleId || isNaN(articleId)) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    getArticleCard(articleId)
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
  }, [articleId]);

  useEffect(() => {
    if (!data || !selectedPersona) return;
    trackEvent({
      user_id: selectedPersona.user_id,
      event_type: "detail_view",
      surface: "article_detail",
      article_id: data.article_id,
    }).then(() => bumpProfile());
  }, [data, selectedPersona, bumpProfile]);

  if (isNaN(articleId)) {
    return (
      <main className="zr-center">
        <div className="zr-status">Invalid article ID.</div>
      </main>
    );
  }

  if (loading) {
    return (
      <main className="zr-center">
        <div className="zr-status">Loading article...</div>
      </main>
    );
  }

  if (error) {
    return (
      <main className="zr-center">
        <div className="zr-status">Failed to load article: {error}</div>
      </main>
    );
  }

  if (!data) {
    return (
      <main className="zr-center">
        <div className="zr-status">Article not found.</div>
      </main>
    );
  }

  const mainCategory = data.categories?.[0];

  return (
    <main className="zr-center">
      <div className="zr-post-detail">
        <Link to="/" className="zr-back-link">
          <ArrowLeft size={14} />
          Back to feed
        </Link>

        <div className="zr-card__meta">
          {mainCategory && (
            <span className="zr-card__community">
              <span
                className="zr-card__avatar"
                style={{
                  background: `linear-gradient(135deg, hsl(${mainCategory.topic_id * 47 % 360}, 60%, 55%), hsl(${mainCategory.topic_id * 83 % 360}, 70%, 65%))`,
                }}
              />
              {mainCategory.display_name}
            </span>
          )}
          <span>Source: {data.source_domain}</span>
        </div>

        <h1 className="zr-post-detail__title">{data.headline}</h1>

        {data.categories.length > 0 && (
          <div className="zr-card__chips">
            {data.categories.map((t) => (
              <span key={t.topic_id} className="zr-chip">
                {t.display_name}
              </span>
            ))}
          </div>
        )}

        <div className="zr-post-detail__summary">{data.abstract}</div>
      </div>
    </main>
  );
}
