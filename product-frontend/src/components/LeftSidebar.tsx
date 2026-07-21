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
        <div className="zr-left__section-title">News Categories</div>
        {["Sports", "Finance", "Science"].map((category, index) => (
          <Link key={category} to="/" className="zr-left__item">
            <span
              className="zr-card__avatar"
              style={{
                width: 24,
                height: 24,
                background: `linear-gradient(135deg, hsl(${(index + 1) * 47 % 360}, 60%, 55%), hsl(${(index + 1) * 83 % 360}, 70%, 65%))`,
              }}
            />
            <span>{category}</span>
          </Link>
        ))}
      </div>
    </nav>
  );
}
