// Single source of truth for talking to the backend.
// Set VITE_API_BASE_URL in .env; defaults to /api (proxied to FastAPI).
const BASE = import.meta.env.VITE_API_BASE_URL || "/api";

// Flip to true to demo the UI with no backend running.
export const USE_MOCK = false;

/** POST /analyze — multipart file upload. Returns { session_id, analysis }. */
export async function analyzeResume(file) {
  if (USE_MOCK) return mockAnalyze();

  const form = new FormData();
  form.append("file", file);

  const res = await fetch(`${BASE}/analyze`, { method: "POST", body: form });
  if (!res.ok) {
    const detail = await safeDetail(res);
    throw new Error(detail || `Analysis failed (${res.status})`);
  }
  return res.json();
}

/**
 * POST /chat — { session_id, message }.
 * Expects { reply, messages_remaining, limit_reached } back.
 * NOTE: the backend /chat endpoint is the next thing to build; this is the
 * contract the frontend is written against.
 */
export async function sendChat(sessionId, message) {
  if (USE_MOCK) return mockChat(message);

  const res = await fetch(`${BASE}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, message }),
  });
  if (!res.ok) {
    const detail = await safeDetail(res);
    throw new Error(detail || `Chat failed (${res.status})`);
  }
  return res.json();
}

async function safeDetail(res) {
  try {
    const data = await res.json();
    return data.detail;
  } catch {
    return null;
  }
}

/* ---------- Mock data (for standalone UI demos) ---------- */
function mockAnalyze() {
  return new Promise((resolve) =>
    setTimeout(
      () =>
        resolve({
          session_id: "mock-session",
          analysis: {
            ats: {
              overall: 85,
              keyword_match: 80,
              formatting: 90,
              quantification: 74,
              notes: [
                "Strong use of technical skills and project descriptions.",
                "Good quantification in the work-experience section.",
              ],
            },
            length: {
              page_count: 1,
              is_appropriate: true,
              verdict: "One page fits the experience shown — keep it tight.",
            },
            sections: [
              {
                section_name: "Profile",
                is_standard: false,
                score: 75,
                strengths: ["Concise summary", "Relevant focus areas"],
                issues: ["Broad claims without concrete evidence"],
                suggestions: ["Lead with a measurable outcome"],
              },
              {
                section_name: "AI & ML Projects",
                is_standard: false,
                score: 90,
                strengths: ["Detailed, specific tech", "GitHub links included"],
                issues: [],
                suggestions: ["Summarize each project's impact in one line"],
              },
              {
                section_name: "Work Experience",
                is_standard: true,
                score: 85,
                strengths: ["Measurable achievements"],
                issues: ["Current role listed last"],
                suggestions: ["Reorder newest-first"],
              },
              {
                section_name: "Education",
                is_standard: true,
                score: 80,
                strengths: ["Relevant degrees"],
                issues: ["Missing expected graduation date"],
                suggestions: ["Add completion timeline"],
              },
            ],
            overall_improvements: [
              "Back up profile claims with concrete evidence.",
              "Quantify achievements in every section.",
              "Add a short accomplishments summary.",
            ],
            primary_path: {
              current_role: "Data Analyst moving toward AI Engineering",
              current_scope:
                "Analytics and BI foundation, with AI projects demonstrating applied ML — not yet a production AI Engineer by track record.",
              future_scope: "AI Engineer, then Senior AI Engineer / Lead.",
              timeline: "12–18 months of production experience to consolidate.",
            },
            parallel_paths: [
              {
                title: "Machine Learning Engineer",
                fit_reason: "Applied ML projects align closely.",
                requirements: ["Model deployment", "MLOps", "System design"],
                effort_level: "low",
              },
              {
                title: "Data Engineer",
                fit_reason: "Strong data/analytics foundation.",
                requirements: ["Pipelines", "Spark", "Warehousing"],
                effort_level: "medium",
              },
            ],
            summary:
              "A strong analytics foundation with genuine applied-AI projects. The resume brands you as an AI Engineer; the evidence shows someone in transition — closing that gap with shipped production work is the highest-leverage move.",
          },
        }),
      1400
    )
  );
}

let mockCount = 0;
function mockChat(message) {
  return new Promise((resolve) =>
    setTimeout(() => {
      mockCount += 1;
      const remaining = Math.max(0, 5 - mockCount);
      resolve({
        reply: `That's a thoughtful question about "${message.slice(
          0,
          40
        )}". In a real session I'd draw on your resume analysis to answer specifically.`,
        messages_remaining: remaining,
        limit_reached: remaining === 0,
      });
    }, 900)
  );
}
