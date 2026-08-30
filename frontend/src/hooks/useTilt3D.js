/**
 * useTilt3D — Mouse-driven 3D perspective tilt effect for cards.
 *
 * Returns ref + style to apply a subtle 3D tilt based on mouse position.
 * Respects prefers-reduced-motion. Cleans up listeners on unmount.
 *
 * Usage:
 *   const { ref, style } = useTilt3D({ maxTilt: 8, glare: true });
 *   <div ref={ref} style={{ ...baseStyle, ...style, transformStyle: 'preserve-3d' }} />
 */

import { useRef, useState, useCallback, useEffect } from 'react';

const prefersReducedMotion =
  typeof window !== 'undefined' &&
  window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;

export default function useTilt3D({
  maxTilt = 8,
  scale = 1.02,
  speed = 400,
  glare = false,
} = {}) {
  const ref = useRef(null);
  const [tiltStyle, setTiltStyle] = useState({});

  const handleMouseMove = useCallback(
    (e) => {
      if (prefersReducedMotion) return;
      const el = ref.current;
      if (!el) return;

      const rect = el.getBoundingClientRect();
      const x = (e.clientX - rect.left) / rect.width;
      const y = (e.clientY - rect.top) / rect.height;

      const tiltX = (0.5 - y) * maxTilt;
      const tiltY = (x - 0.5) * maxTilt;

      setTiltStyle({
        transform: `perspective(800px) rotateX(${tiltX}deg) rotateY(${tiltY}deg) scale3d(${scale}, ${scale}, ${scale})`,
        transition: `transform ${speed}ms cubic-bezier(0.22, 1, 0.36, 1)`,
        ...(glare
          ? {
              '--glare-x': `${x * 100}%`,
              '--glare-y': `${y * 100}%`,
            }
          : {}),
      });
    },
    [maxTilt, scale, speed, glare]
  );

  const handleMouseLeave = useCallback(() => {
    setTiltStyle({
      transform: 'perspective(800px) rotateX(0deg) rotateY(0deg) scale3d(1, 1, 1)',
      transition: `transform ${speed}ms cubic-bezier(0.22, 1, 0.36, 1)`,
    });
  }, [speed]);

  useEffect(() => {
    const el = ref.current;
    if (!el || prefersReducedMotion) return;

    el.addEventListener('mousemove', handleMouseMove);
    el.addEventListener('mouseleave', handleMouseLeave);
    return () => {
      el.removeEventListener('mousemove', handleMouseMove);
      el.removeEventListener('mouseleave', handleMouseLeave);
    };
  }, [handleMouseMove, handleMouseLeave]);

  return { ref, style: tiltStyle };
}
