import { MessageCircle, Share2 } from "lucide-react";
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
  const mainTopic = item.topics?.[0];
  const communityName = mainTopic ? `r/topic-${mainTopic.topic_id}` : "r/zhihurec";

  return (
    <div className="zr-card">
      <VoteActions
        answerId={item.answer_id}
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
                background: `linear-gradient(135deg, hsl(${(mainTopic?.topic_id ?? 1) * 47 % 360}, 60%, 55%), hsl(${(mainTopic?.topic_id ?? 1) * 83 % 360}, 70%, 65%))`,
              }}
            />
            {communityName}
          </span>
          {"author" in item && <span>Posted by u/user-{item.author.author_id}</span>}
        </div>

        <h3 className="zr-card__title">
          <Link to={`/post/${item.answer_id}`} onClick={onTrackClick}>
            {item.question_title}
          </Link>
        </h3>

        <p className="zr-card__summary">{item.answer_summary}</p>

        {item.topics.length > 0 && (
          <div className="zr-card__chips">
            {item.topics.map((t) => (
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
          <Link to={`/post/${item.answer_id}`} className="zr-action" onClick={onTrackClick}>
            <MessageCircle size={16} />
            Comments
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
