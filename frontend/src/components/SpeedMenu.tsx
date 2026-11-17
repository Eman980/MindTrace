import { useEffect, useRef, useState } from "react";

const SPEEDS = [0.5, 0.75, 1, 1.25, 1.5, 2];

type Props = {
  mediaRef: React.RefObject<HTMLMediaElement | null>;
  value: number;
  onChange: (speed: number) => void;
};

export default function SpeedMenu({ mediaRef, value, onChange }: Props) {
  const [open, setOpen] = useState(false);
  const boxRef = useRef<HTMLDivElement>(null);

  // Apply the speed whenever it changes
  useEffect(() => {
    if (mediaRef.current) mediaRef.current.playbackRate = value;
  }, [value, mediaRef]);

  // Close when clicking outside
  useEffect(() => {
    const close = (e: MouseEvent) => {
      if (boxRef.current && !boxRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, []);

  return (
    <div ref={boxRef} style={{ position: "relative", display: "inline-block" }}>
      <button
        type="button"
        aria-label="Playback speed"
        aria-haspopup="menu"
        aria-expanded={open}
        onClick={() => setOpen((o) => !o)}
        style={{
          padding: "6px 10px",
          borderRadius: 8,
          border: "1px solid rgba(255,255,255,0.3)",
          background: "rgba(0,0,0,0.5)",
          color: "#fff",
          cursor: "pointer",
          fontSize: 13,
        }}
      >
        {value}x
      </button>

      {open && (
        <div
          role="menu"
          style={{
            position: "absolute",
            bottom: "100%",
            right: 0,
            marginBottom: 6,
            zIndex: 9999,
            background: "rgba(20,20,30,0.97)",
            borderRadius: 8,
            padding: 4,
            minWidth: 72,
            boxShadow: "0 4px 16px rgba(0,0,0,0.4)",
          }}
        >
          {SPEEDS.map((s) => (
            <button
              key={s}
              type="button"
              role="menuitem"
              onClick={() => {
                onChange(s);
                setOpen(false);
              }}
              style={{
                display: "block",
                width: "100%",
                padding: "6px 12px",
                textAlign: "left",
                border: "none",
                borderRadius: 6,
                cursor: "pointer",
                fontSize: 13,
                color: "#fff",
                background: s === value ? "rgba(255,255,255,0.2)" : "transparent",
              }}
            >
              {s}x
            </button>
          ))}
        </div>
      )}
    </div>
  );
}