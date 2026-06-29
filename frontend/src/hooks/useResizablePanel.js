import { useCallback, useState } from "react";

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value));
}

export function useResizablePanel(initialWidth, { min, max, direction = 1 }) {
  const [width, setWidth] = useState(initialWidth);

  const startResize = useCallback(
    (event) => {
      event.preventDefault();
      const startX = event.clientX;
      const startWidth = width;

      // Pointer listeners live on `window` so resizing continues even if the
      // cursor temporarily leaves the narrow drag handle.
      function handlePointerMove(moveEvent) {
        const delta = (moveEvent.clientX - startX) * direction;
        setWidth(clamp(startWidth + delta, min, max));
      }

      function handlePointerUp() {
        window.removeEventListener("pointermove", handlePointerMove);
        window.removeEventListener("pointerup", handlePointerUp);
      }

      window.addEventListener("pointermove", handlePointerMove);
      window.addEventListener("pointerup", handlePointerUp);
    },
    [direction, max, min, width],
  );

  return { width, startResize };
}
