import { Route, Routes } from "react-router-dom";
import { Navbar } from "@/components/Navbar";
import { AnalysisPage } from "@/pages/AnalysisPage";
import { DashboardPage } from "@/pages/DashboardPage";
import { OpeningsPage } from "@/pages/OpeningsPage";
import { PlayPage } from "@/pages/PlayPage";
import { PuzzlePage } from "@/pages/PuzzlePage";
import { ReviewPage } from "@/pages/ReviewPage";
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
          <Route path="/dashboard" element={<DashboardPage />} />
        </Routes>
      </main>
    </div>
  );
}
