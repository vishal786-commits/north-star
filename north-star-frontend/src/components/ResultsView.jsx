import { CircularScore, MiniRing, ProgressBar } from "./Primitives";
import ChatPanel from "./ChatPanel";
import { scoreBand } from "../hooks";

export default function ResultsView({ data, onReset }) {
  const { analysis, session_id } = data;
  const { ats, length, sections, overall_improvements, primary_path, parallel_paths, summary } =
    analysis;
  const celebrate = ats.overall >= 80;

  return (
    <div className="shell">
      <div className="grid">
        {/* HERO — the centerpiece */}
        <section className={`hero glass reveal ${celebrate ? "celebrate" : ""}`}>
          <div className="ring-wrap">
            <div className="sparkles" aria-hidden="true">
              <span></span><span></span><span></span><span></span><span></span>
            </div>
            <CircularScore score={ats.overall} label="Resume score" />
          </div>
          <div className="hero-copy">
            <p className="eyebrow">Your north star reading</p>
            <p className="hero-verdict">{summary}</p>
            <button className="btn btn-ghost" onClick={onReset}>
              Analyze another resume
            </button>
          </div>
        </section>

        {/* ATS breakdown + Length */}
        <div className="grid two-col">
          <section className="card glass reveal" style={{ animationDelay: "0.05s" }}>
            <div className="section-title">
              <h2 className="display" style={{ fontSize: "1.25rem" }}>
                ATS breakdown
              </h2>
              <span className="badge">{ats.overall} / 100</span>
            </div>
            <ProgressBar label="Keyword match" score={ats.keyword_match} delay={300} />
            <ProgressBar label="Formatting" score={ats.formatting} delay={450} />
            <ProgressBar label="Quantification" score={ats.quantification} delay={600} />
            <ul className="notes">
              {ats.notes.map((n, i) => (
                <li key={i}>{n}</li>
              ))}
            </ul>
          </section>

          <section className="card glass reveal" style={{ animationDelay: "0.1s" }}>
            <div className="section-title">
              <h2 className="display" style={{ fontSize: "1.25rem" }}>
                Length
              </h2>
              <span className={`badge ${length.is_appropriate ? "effort-low" : "effort-high"}`}>
                {length.page_count} page{length.page_count > 1 ? "s" : ""}
              </span>
            </div>
            <p style={{ color: "var(--text)", lineHeight: 1.6 }}>{length.verdict}</p>
            <p className="muted" style={{ marginTop: 12, fontSize: "0.86rem" }}>
              {length.is_appropriate
                ? "The length is justified by the content."
                : "Consider tightening — unjustified length dilutes impact."}
            </p>
          </section>
        </div>

        {/* SECTIONS */}
        <section className="reveal" style={{ animationDelay: "0.15s" }}>
          <h2 className="display" style={{ fontSize: "1.4rem", margin: "16px 0 4px" }}>
            Section by section
          </h2>
          <p className="muted" style={{ marginBottom: 18 }}>
            Every section it found — including the ones you invented.
          </p>
          <div className="grid two-col">
            {sections.map((s, i) => (
              <SectionCard key={i} s={s} />
            ))}
          </div>
        </section>

        {/* CAREER PATHS */}
        <section className="path-primary glass reveal" style={{ animationDelay: "0.1s" }}>
          <h2 className="display" style={{ fontSize: "1.4rem", marginBottom: 4 }}>
            Where this points
          </h2>
          <p className="muted">Based on demonstrated evidence, not the resume's branding.</p>
          <div className="path-flow">
            <div className="flow-node">
              <span className="stage">Now</span>
              <p className="role">{primary_path.current_role}</p>
              <p className="muted" style={{ fontSize: "0.88rem" }}>
                {primary_path.current_scope}
              </p>
            </div>
            <div className="flow-arrow" aria-hidden="true">
              →
            </div>
            <div className="flow-node">
              <span className="stage">Next</span>
              <p className="role">{primary_path.future_scope}</p>
              <p className="muted" style={{ fontSize: "0.88rem" }}>
                {primary_path.timeline}
              </p>
            </div>
          </div>
        </section>

        {/* PARALLEL PATHS */}
        <section className="reveal" style={{ animationDelay: "0.12s" }}>
          <h2 className="display" style={{ fontSize: "1.4rem", margin: "16px 0 18px" }}>
            Parallel paths
          </h2>
          <div className="grid parallel-grid">
            {parallel_paths.map((p, i) => (
              <div key={i} className="parallel-card glass">
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <h4>{p.title}</h4>
                  <span className={`badge effort-${p.effort_level}`}>{p.effort_level} effort</span>
                </div>
                <p className="muted" style={{ fontSize: "0.9rem" }}>
                  {p.fit_reason}
                </p>
                <div className="req-list">
                  {p.requirements.map((r, j) => (
                    <span key={j} className="req">
                      {r}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* OVERALL IMPROVEMENTS */}
        <section className="card glass reveal" style={{ animationDelay: "0.1s" }}>
          <h2 className="display" style={{ fontSize: "1.25rem", marginBottom: 14 }}>
            Fix these first
          </h2>
          <ul className="notes">
            {overall_improvements.map((imp, i) => (
              <li key={i}>{imp}</li>
            ))}
          </ul>
        </section>

        {/* CHAT */}
        <section className="reveal" style={{ animationDelay: "0.1s" }}>
          <ChatPanel sessionId={session_id} />
        </section>
      </div>
    </div>
  );
}

function SectionCard({ s }) {
  const { band } = scoreBand(s.score);
  return (
    <div className="section-card glass">
      <div className="head">
        <MiniRing score={s.score} />
        <div>
          <h3>{s.section_name}</h3>
          <div className="chip-row">
            {!s.is_standard && <span className="badge custom">Custom section</span>}
            <span className={`badge effort-${band === "high" ? "low" : band === "mid" ? "medium" : "high"}`}>
              {s.score} / 100
            </span>
          </div>
        </div>
      </div>

      {s.strengths.length > 0 && (
        <div className="detail good">
          <h4>Strengths</h4>
          <ul>
            {s.strengths.map((x, i) => (
              <li key={i}>{x}</li>
            ))}
          </ul>
        </div>
      )}
      {s.issues.length > 0 && (
        <div className="detail bad">
          <h4>Issues</h4>
          <ul>
            {s.issues.map((x, i) => (
              <li key={i}>{x}</li>
            ))}
          </ul>
        </div>
      )}
      {s.suggestions.length > 0 && (
        <div className="detail tip">
          <h4>Suggestions</h4>
          <ul>
            {s.suggestions.map((x, i) => (
              <li key={i}>{x}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
