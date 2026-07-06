import { useEffect, useRef, useState } from "react";
import { sendChat } from "../api";

// Purely cosmetic pip count; the server is the source of truth for the real
// limit (messages_remaining). If your backend limit differs, the pips still
// render sensibly and the input locks based on the server response.
const MAX_PIPS = 7;

export default function ChatPanel({ sessionId }) {
  const [log, setLog] = useState([
    {
      role: "bot",
      text: "Ask me anything about your analysis — a section, a career path, or what to fix first.",
    },
  ]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [used, setUsed] = useState(0);
  const [locked, setLocked] = useState(false);
  const [error, setError] = useState("");
  const logRef = useRef(null);

  useEffect(() => {
    logRef.current?.scrollTo({ top: logRef.current.scrollHeight, behavior: "smooth" });
  }, [log, sending]);

  async function submit() {
    const msg = input.trim();
    if (!msg || sending || locked) return;

    setInput("");
    setError("");
    setLog((l) => [...l, { role: "user", text: msg }]);
    setSending(true);

    try {
      const res = await sendChat(sessionId, msg);
      setLog((l) => [...l, { role: "bot", text: res.reply }]);
      setUsed((u) => u + 1);
      if (res.limit_reached || res.messages_remaining === 0) setLocked(true);
    } catch (e) {
      setLog((l) => [
        ...l,
        { role: "bot", text: "Something went wrong reaching the coach. Try again in a moment." },
      ]);
      setError(e.message);
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="chat glass">
      <div className="chat-meta">
        <span className="eyebrow">Coach chat</span>
        <div className="pips" aria-label={`${used} of ${MAX_PIPS} messages used`}>
          {Array.from({ length: MAX_PIPS }).map((_, i) => (
            <span key={i} className={`pip ${i < used ? "used" : ""}`} />
          ))}
        </div>
      </div>

      <div className="chat-log" ref={logRef}>
        {log.map((m, i) => (
          <div key={i} className={`bubble ${m.role}`}>
            {m.text}
          </div>
        ))}
        {sending && (
          <div className="bubble bot typing" aria-label="Coach is typing">
            <span></span>
            <span></span>
            <span></span>
          </div>
        )}
      </div>

      <div className="chat-input">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && submit()}
          placeholder={locked ? "Session limit reached" : "Ask about your resume…"}
          disabled={locked || sending}
          aria-label="Message the coach"
        />
        <button className="btn" onClick={submit} disabled={locked || sending || !input.trim()}>
          Send
        </button>
      </div>
      {locked && (
        <p className="muted" style={{ marginTop: 10, fontSize: "0.82rem" }}>
          You've reached this session's message limit. Re-upload to start fresh.
        </p>
      )}
    </div>
  );
}
