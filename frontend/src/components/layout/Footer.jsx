/**
 * Footer — Application footer for public pages.
 *
 * Clean, institutional. Links to about, data sources, privacy.
 * Not used in government shell.
 */

import { Link } from 'react-router-dom';

export default function Footer() {
  return (
    <footer className="app-footer" role="contentinfo">
      <div className="app-footer__inner">
        <div className="app-footer__left">
          <span className="app-footer__brand">Lahore+</span>
          <span className="app-footer__sep">·</span>
          <span className="app-footer__tagline">Civic Environmental Intelligence</span>
        </div>
        <nav className="app-footer__links" aria-label="Footer navigation">
          <Link to="/reports" className="app-footer__link">Reports</Link>
          <Link to="/insights" className="app-footer__link">Insights</Link>
          <span className="app-footer__link app-footer__link--muted">Privacy</span>
          <span className="app-footer__link app-footer__link--muted">Data Sources</span>
        </nav>
        <div className="app-footer__right">
          <span className="app-footer__copy">© {new Date().getFullYear()} Lahore+</span>
        </div>
      </div>
    </footer>
  );
}
