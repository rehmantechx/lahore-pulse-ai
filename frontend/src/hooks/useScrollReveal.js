/**
 * useScrollReveal — IntersectionObserver-based scroll reveal with 3D depth.
 *
 * Elements fade in with perspective transforms as they enter the viewport.
 * Supports staggered children, configurable threshold, and respects
 * prefers-reduced-motion.
 *
 * Usage:
 *   const { ref, isVisible } = useScrollReveal({ threshold: 0.15 });
 *   <div ref={ref} className={isVisible ? 'scroll-revealed' : 'scroll-hidden'} />
 */

import { useRef, useState, useEffect, useCallback } from 'react';

const prefersReducedMotion =
  typeof window !== 'undefined' &&
  window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;

const hasIntersectionObserver =
  typeof window !== 'undefined' && typeof window.IntersectionObserver !== 'undefined';

// When IO isn't available (e.g. jsdom / SSR), default to visible
const defaultVisible = prefersReducedMotion || !hasIntersectionObserver;

export default function useScrollReveal({
  threshold = 0.12,
  rootMargin = '0px 0px -40px 0px',
  triggerOnce = true,
} = {}) {
  const ref = useRef(null);
  const [isVisible, setIsVisible] = useState(defaultVisible);

  const handleIntersect = useCallback(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          setIsVisible(true);
        } else if (!triggerOnce) {
          setIsVisible(false);
        }
      });
    },
    [triggerOnce]
  );

  useEffect(() => {
    if (!hasIntersectionObserver || prefersReducedMotion) return;
    const node = ref.current;
    if (!node) return;

    const observer = new IntersectionObserver(handleIntersect, {
      threshold,
      rootMargin,
    });

    observer.observe(node);
    return () => observer.disconnect();
  }, [handleIntersect, threshold, rootMargin]);

  return { ref, isVisible };
}
