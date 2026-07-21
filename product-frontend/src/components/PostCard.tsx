import { Newspaper, Share2 } from "lucide-react";
import { Link } from "react-router-dom";
import type { FeedItem, SearchItem } from "../api/types";
import VoteActions from "./VoteActions";

interface Props {
  item: FeedItem | SearchItem;
  userId: number;
  requestId?: string;
  surface?: string;
  showReason?: boolean;
  onTrackClick?: () => void;
  onProfileChanged?: () => void;
}

function isFeedItem(item: FeedItem | SearchItem): item is FeedItem {
  return "selected_reason" in item;
}

export default function PostCard({
  item,
  userId,
  requestId,
  surface = "feed",
  showReason,
  onTrackClick,
  onProfileChanged,
}: Props) {
  const mainCategory = item.categories?.[0];
  const categoryName = mainCategory?.display_name ?? "News";

  return (
    <div className="zr-card">
      <VoteActions
        articleId={item.article_id}
        userId={userId}
        requestId={requestId}
        surface={surface}
        onVoted={onProfileChanged}
      />

      <div className="zr-card__body">
        <div className="zr-card__meta">
          <span className="zr-card__community">
            <span
              className="zr-card__avatar"
              style={{
                background: `linear-gradient(135deg, hsl(${(mainCategory?.topic_id ?? 1) * 47 % 360}, 60%, 55%), hsl(${(mainCategory?.topic_id ?? 1) * 83 % 360}, 70%, 65%))`,
              }}
            />
            {categoryName}
          </span>
          {isFeedItem(item) && item.content_type === "sponsored" && (
            <span className="zr-card__sponsored">{item.sponsored?.label ?? "Sponsored"}</span>
          )}
          <span>Source: {item.source_domain}</span>
        </div>

        <h3 className="zr-card__title">
          <Link to={`/articles/${item.article_id}`} onClick={onTrackClick}>
            {item.headline}
          </Link>
        </h3>

        <p className="zr-card__summary">{item.abstract}</p>

        {item.categories.length > 0 && (
          <div className="zr-card__chips">
            {item.categories.map((t) => (
              <span key={t.topic_id} className="zr-chip">
                {t.display_name}
              </span>
            ))}
          </div>
        )}

        {showReason && isFeedItem(item) && item.selected_reason && (
          <div className="zr-card__reason">{item.selected_reason}</div>
        )}

        <div className="zr-card__actions">
          <Link
            to={`/articles/${item.article_id}`}
            className="zr-action"
            onClick={onTrackClick}
          >
            <Newspaper size={16} />
            Details
          </Link>
          <button className="zr-action">
            <Share2 size={16} />
            Share
          </button>
        </div>
      </div>
    </div>
  );
}
