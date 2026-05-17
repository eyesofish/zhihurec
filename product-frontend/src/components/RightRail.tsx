import { usePersona } from "../context/PersonaContext";
import ProfileDebugPanel from "./ProfileDebugPanel";

export default function RightRail() {
  const { selectedPersona, refreshTick } = usePersona();

  return (
    <aside className="zr-right">
      <div className="zr-rail-card">
        <div className="zr-rail-card__title">Recent Posts</div>
        <div style={{ fontSize: 13, color: "var(--zr-text-muted)" }}>
          Browse the feed and click posts to see them here.
        </div>
      </div>

      {selectedPersona && (
        <ProfileDebugPanel userId={selectedPersona.user_id} refreshTick={refreshTick} />
      )}
    </aside>
  );
}
