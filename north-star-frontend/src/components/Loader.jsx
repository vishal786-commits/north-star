import { StarMark } from "./Primitives";

const LINES = [
  "Reading your resume…",
  "Mapping every section…",
  "Weighing evidence against claims…",
  "Charting where it points…",
];

export default function Loader({ step = 0 }) {
  return (
    <div className="loader-stage reveal">
      <div>
        <div className="loader-star">
          <StarMark size={64} />
        </div>
        <p className="display" style={{ fontSize: "1.3rem" }}>
          {LINES[step % LINES.length]}
        </p>
        <p className="muted" style={{ marginTop: 8 }}>
          This takes a few seconds.
        </p>
      </div>
    </div>
  );
}
