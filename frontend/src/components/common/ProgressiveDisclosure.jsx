/**
 * ProgressiveDisclosure — Expandable section for deep-dive content.
 *
 * Used for sections that contain detail information officers may want
 * to inspect but don't need to see immediately. Follows the pattern:
 *   - Primary info is always visible
 *   - Secondary/optional info is behind a toggle
 *
 * Respects prefers-reduced-motion.
 * Keyboard accessible: Enter/Space toggles.
 */

import { useState } from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';

export default function ProgressiveDisclosure({
  label = 'Show details',
  labelExpanded = 'Hide details',
  defaultExpanded = false,
  children,
  testId,
  className = '',
}) {
  const [expanded, setExpanded] = useState(defaultExpanded);

  return (
    <div className={`pd ${className}`} data-testid={testId}>
      <button
        className="pd__toggle"
        onClick={() => setExpanded(!expanded)}
        aria-expanded={expanded}
        data-testid={testId ? `${testId}-toggle` : undefined}
      >
        {expanded ? (
          <ChevronDown size={14} className="pd__icon" aria-hidden="true" />
        ) : (
          <ChevronRight size={14} className="pd__icon" aria-hidden="true" />
        )}
        <span className="pd__label">{expanded ? labelExpanded : label}</span>
      </button>
      {expanded && (
        <div className="pd__content" data-testid={testId ? `${testId}-content` : undefined}>
          {children}
        </div>
      )}
    </div>
  );
}
