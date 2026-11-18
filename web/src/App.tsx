import { Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
import OverviewPage from "./pages/OverviewPage";
import FunnelPage from "./pages/FunnelPage";
import RetentionPage from "./pages/RetentionPage";
import FeaturesPage from "./pages/FeaturesPage";
import ExperimentPage from "./pages/ExperimentPage";
import InsightsPage from "./pages/InsightsPage";

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<OverviewPage />} />
        <Route path="/funnel" element={<FunnelPage />} />
        <Route path="/retention" element={<RetentionPage />} />
        <Route path="/features" element={<FeaturesPage />} />
        <Route path="/experiment" element={<ExperimentPage />} />
        <Route path="/insights" element={<InsightsPage />} />
      </Routes>
    </Layout>
  );
}
