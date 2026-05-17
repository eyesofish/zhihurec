import { Home, Flame, Compass, Plus } from "lucide-react";
import { Link } from "react-router-dom";

export default function LeftSidebar() {
  return (
    <nav className="zr-left">
      <div className="zr-left__section">
        <Link to="/" className="zr-left__item zr-left__item--active">
          <Home size={20} />
          <span>Home</span>
        </Link>
        <Link to="/" className="zr-left__item">
          <Flame size={20} />
          <span>Popular</span>
        </Link>
        <Link to="/" className="zr-left__item">
          <Compass size={20} />
          <span>Explore</span>
        </Link>
      </div>

      <div className="zr-left__section">
        <div className="zr-left__section-title">Custom Feeds</div>
        <Link to="/" className="zr-left__item">
          <Plus size={20} />
          <span>Create a custom feed</span>
        </Link>
      </div>

      <div className="zr-left__section">
        <div className="zr-left__section-title">Communities</div>
        {[1, 2, 3].map((id) => (
          <Link key={id} to="/" className="zr-left__item">
            <span
              className="zr-card__avatar"
              style={{
                width: 24,
                height: 24,
                background: `linear-gradient(135deg, hsl(${id * 47 % 360}, 60%, 55%), hsl(${id * 83 % 360}, 70%, 65%))`,
              }}
            />
            <span>r/topic-{id}</span>
          </Link>
        ))}
      </div>
    </nav>
  );
}
