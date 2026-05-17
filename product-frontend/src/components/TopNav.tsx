import { Bell, Plus, MessageSquare } from "lucide-react";
import { Link } from "react-router-dom";
import PersonaSwitcher from "./PersonaSwitcher";
import SearchBox from "./SearchBox";

export default function TopNav() {

  return (
    <header className="zr-topbar">
      <div className="zr-topbar__brand">
        <Link to="/">zhihurec</Link>
      </div>

      <div className="zr-topbar__search">
        <SearchBox />
      </div>

      <div className="zr-topbar__actions">
        <button className="zr-topbar__action-icon" aria-label="Messages">
          <MessageSquare size={18} />
        </button>
        <button className="zr-topbar__action-icon" aria-label="Create post">
          <Plus size={18} />
        </button>
        <button className="zr-topbar__action-icon" aria-label="Notifications">
          <Bell size={18} />
        </button>
        <PersonaSwitcher />
      </div>
    </header>
  );
}
