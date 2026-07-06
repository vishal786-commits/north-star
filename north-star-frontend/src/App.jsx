import { useEffect, useState } from "react";
import TopBar from "./components/TopBar";
import UploadView from "./components/UploadView";
import Loader from "./components/Loader";
import ResultsView from "./components/ResultsView";
import { analyzeResume } from "./api";

export default function App() {
  const [stage, setStage] = useState("upload"); // upload | loading | results
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [loaderStep, setLoaderStep] = useState(0);

  // Cycle loader copy while analyzing.
  useEffect(() => {
    if (stage !== "loading") return;
    const id = setInterval(() => setLoaderStep((s) => s + 1), 1600);
    return () => clearInterval(id);
  }, [stage]);

  async function handleAnalyze(file) {
    setError("");
    setStage("loading");
    setLoaderStep(0);
    try {
      const result = await analyzeResume(file);
      setData(result);
      setStage("results");
    } catch (e) {
      setError(e.message || "Something went wrong. Try again.");
      setStage("upload");
    }
  }

  function reset() {
    setData(null);
    setError("");
    setStage("upload");
  }

  return (
    <>
      <div className="aurora">
        <div className="starfield" />
      </div>
      <TopBar />
      {stage === "upload" && (
        <div className="shell">
          <UploadView onAnalyze={handleAnalyze} error={error} />
        </div>
      )}
      {stage === "loading" && (
        <div className="shell">
          <Loader step={loaderStep} />
        </div>
      )}
      {stage === "results" && data && <ResultsView data={data} onReset={reset} />}
    </>
  );
}
