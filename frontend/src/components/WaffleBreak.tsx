import { useEffect, useRef, useState } from "react";

/** A small celebration when every file is closed. It only fires when the board
 *  goes from "something open" to "all closed" while you're watching, never on page load.
 *  `allClear` is null until the tickets have loaded. */
export function WaffleBreak({ allClear }: { allClear: boolean | null }) {
  const [show, setShow] = useState(false);
  const prev = useRef<boolean | null>(null);

  useEffect(() => {
    if (allClear === null) return;
    const was = prev.current;
    prev.current = allClear;
    if (was === false && allClear) {
      setShow(true);
      const t = setTimeout(() => setShow(false), 5200);
      return () => clearTimeout(t);
    }
  }, [allClear]);

  if (!show) return null;
  return (
    <div className="waffle-break" onClick={() => setShow(false)} role="status">
      {Array.from({ length: 18 }, (_, i) => (
        <span
          key={i}
          className="waffle"
          style={{ left: `${(i * 53) % 100}%`, animationDelay: `${(i % 6) * 0.25}s`, fontSize: `${22 + (i % 4) * 6}px` }}
        >
          🧇
        </span>
      ))}
      <div className="waffle-card">
        <div className="waffle-title">Every file is closed.</div>
        <div className="hand">Waffle break. You've earned it.</div>
      </div>
    </div>
  );
}
