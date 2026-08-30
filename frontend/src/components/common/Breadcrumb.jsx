/**
 * Breadcrumb — Shared navigation breadcrumb.
 *
 * Renders: Home (/) > {Page Name}  [Date]
 *
 * Props:
 *   pageName  — current page title (e.g., "Alerts", "Reports")
 *   showDate  — whether to show today's date on the right (default true)
 *   dateStr   — custom date string; if omitted, auto-formats today
 */

import { Link } from 'react-router-dom';
import { ChevronRight } from 'lucide-react';

export default function Breadcrumb({ pageName, showDate = true, dateStr }) {
  const today =
    dateStr ||
    new Date().toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });

  return (
    <nav className="lh-breadcrumb" aria-label="Breadcrumb">
      <Link to="/" className="lh-breadcrumb__link">
        Lahore
      </Link>
      <ChevronRight size={14} className="lh-breadcrumb__sep" />
      <span className="lh-breadcrumb__current">{pageName}</span>
      {showDate && <span className="lh-breadcrumb__date">{today}</span>}
    </nav>
  );
}
