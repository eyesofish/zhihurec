import { Route, Routes } from "react-router-dom";
import LeftSidebar from "./components/LeftSidebar";
import RightRail from "./components/RightRail";
import TopNav from "./components/TopNav";
import { PersonaProvider } from "./context/PersonaContext";
import FeedPage from "./pages/FeedPage";
import PostDetailPage from "./pages/PostDetailPage";
import SearchPage from "./pages/SearchPage";

export default function App() {
  return (
    <PersonaProvider>
      <TopNav />
      <div className="zr-shell">
        <LeftSidebar />
        <Routes>
          <Route path="/" element={<FeedPage />} />
          <Route path="/search" element={<SearchPage />} />
          <Route path="/post/:answerId" element={<PostDetailPage />} />
        </Routes>
        <RightRail />
      </div>
    </PersonaProvider>
  );
}
