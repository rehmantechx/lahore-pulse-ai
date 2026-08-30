/**
 * PageTransition — Subtle CSS-based page transition wrapper.
 *
 * Wraps route content and triggers a fade+slide animation on mount.
 * The animation fires automatically when the component remounts
 * (which happens on route change because we use key={pathname}).
 *
 * Respects prefers-reduced-motion — animation is disabled entirely.
 *
 * Architecture:
 * - Parent provides key={location.pathname} to force remount
 * - This component applies the entrance animation class on mount
 * - No exit animation needed — the old component unmounts instantly
 *   while the new one fades in, creating a clean crossfade feel
 */

import { useLocation } from 'react-router-dom';

export default function PageTransition({ children }) {
  return (
    <div className="lp-page-transition">
      {children}
    </div>
  );
}
