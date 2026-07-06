import { useRef, useState } from "react";
import { StarMark } from "./Primitives";

export default function UploadView({ onAnalyze, error }) {
  const inputRef = useRef(null);
  const [file, setFile] = useState(null);
  const [drag, setDrag] = useState(false);
  const [localErr, setLocalErr] = useState("");

  function pick(f) {
    if (!f) return;
    if (f.type !== "application/pdf") {
      setLocalErr("Please choose a PDF file.");
      return;
    }
    setLocalErr("");
    setFile(f);
  }

  return (
    <div className="upload-stage reveal">
      <div className="upload-card glass">
        <div style={{ width: 52, height: 52, margin: "0 auto 20px" }}>
          <StarMark size={52} />
        </div>
        <p className="eyebrow">AI Career Coach</p>
        <h1 className="display" style={{ margin: "8px 0 12px" }}>
          Find out where your resume points.
        </h1>
        <p className="muted">
          Upload your resume and get a section-by-section read — honest scores,
          concrete fixes, and the career paths it opens.
        </p>

        <div
          className={`dropzone ${drag ? "drag" : ""}`}
          onClick={() => inputRef.current?.click()}
          onDragOver={(e) => {
            e.preventDefault();
            setDrag(true);
          }}
          onDragLeave={() => setDrag(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDrag(false);
            pick(e.dataTransfer.files?.[0]);
          }}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => e.key === "Enter" && inputRef.current?.click()}
        >
          <input
            ref={inputRef}
            type="file"
            accept="application/pdf"
            hidden
            onChange={(e) => pick(e.target.files?.[0])}
          />
          {file ? (
            <p className="file-name">{file.name}</p>
          ) : (
            <p className="muted">Drag a PDF here, or click to browse</p>
          )}
        </div>

        {(localErr || error) && <p className="err">{localErr || error}</p>}

        <div style={{ marginTop: 24 }}>
          <button className="btn" disabled={!file} onClick={() => onAnalyze(file)}>
            Analyze resume
          </button>
        </div>
      </div>
    </div>
  );
}
