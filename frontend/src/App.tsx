import { Route, Routes } from "react-router-dom";
import { Navbar } from "@/components/Navbar";
import { AnalysisPage } from "@/pages/AnalysisPage";
import { DashboardPage } from "@/pages/DashboardPage";
import { OpeningsPage } from "@/pages/OpeningsPage";
import { PlayPage } from "@/pages/PlayPage";
import { PlayersPage } from "@/pages/PlayersPage";
import { PuzzlePage } from "@/pages/PuzzlePage";
import { ReviewPage } from "@/pages/ReviewPage";
import { SharedGamePage } from "@/pages/SharedGamePage";
import { TrainingPage } from "@/pages/TrainingPage";

export default function App() {
  return (
    <div className="min-h-full">
      <Navbar />
      <main className="animate-fade-up">
        <Routes>
          <Route path="/" element={<AnalysisPage />} />
          <Route path="/play" element={<PlayPage />} />
          <Route path="/review" element={<ReviewPage />} />
          <Route path="/openings" element={<OpeningsPage />} />
          <Route path="/puzzles" element={<PuzzlePage />} />
          <Route path="/training" element={<TrainingPage />} />
          <Route path="/players" element={<PlayersPage />} />
          <Route path="/shared/:token" element={<SharedGamePage />} />
          <Route path="/dashboard" element={<DashboardPage />} />
        </Routes>
      </main>
    </div>
  );
}
