import { ArrowUp, ArrowDown } from "lucide-react";
import { trackEvent } from "../api/client";

interface Props {
  articleId: number;
  userId: number;
  requestId?: string;
  surface?: string;
  onVoted?: () => void;
}

export default function VoteActions({
  articleId,
  userId,
  requestId,
  surface = "feed",
  onVoted,
}: Props) {
  const handleVote = (direction: "upvote" | "downvote") => {
    trackEvent({
      user_id: userId,
      event_type: direction,
      surface,
      article_id: articleId,
      request_id: requestId ?? null,
    }).then(() => onVoted?.());
  };

  return (
    <div className="zr-card__votes">
      <button
        className="zr-vote-btn zr-vote-btn--up"
        aria-label="Upvote"
        onClick={() => handleVote("upvote")}
      >
        <ArrowUp size={18} />
      </button>
      <span className="zr-vote-count">0</span>
      <button
        className="zr-vote-btn zr-vote-btn--down"
        aria-label="Downvote"
        onClick={() => handleVote("downvote")}
      >
        <ArrowDown size={18} />
      </button>
    </div>
  );
}
