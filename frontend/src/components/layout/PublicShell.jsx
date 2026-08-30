/**
 * PublicShell — Layout wrapper for public/citizen-facing routes.
 *
 * Structure: GlobalHeader (with PublicNav) → content → Footer
 * Uses Outlet pattern for react-router nested routes.
 */

import { Outlet, useLocation } from 'react-router-dom';
import GlobalHeader from './GlobalHeader.jsx';
import PublicNav from './PublicNav.jsx';
import Footer from './Footer.jsx';
import PageTransition from '../common/PageTransition.jsx';

export default function PublicShell() {
  const location = useLocation();

  return (
    <div className="app app--public">
      <a href="#main-content" className="skip-link">Skip to content</a>
      <GlobalHeader mode="public">
        <PublicNav />
      </GlobalHeader>
      <main id="main-content" className="app-content" role="main" tabIndex={-1}>
        <PageTransition key={location.pathname}>
          <Outlet />
        </PageTransition>
      </main>
      <Footer />
    </div>
  );
}
