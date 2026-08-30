/**
 * GlobalHeader — Top-level application header.
 *
 * Layout: [LP Logo + LAHORE PLUS] | [Contextual Nav] | [Status + Notifications + Profile]
 *
 * Wraps PublicNav (for public routes) or GovernmentNav (for government routes).
 * Uses the new warm civic palette — white background, charcoal text, green accent.
 */

import { useState, useRef, useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';
import LPLogo from '../brand/LPLogo.jsx';
import { useHealth } from '../../hooks/useHealth.js';

const STATUS_LABEL = {
  online: 'Connected',
  offline: 'Offline',
  loading: 'Connecting…',
};

export default function GlobalHeader({ mode = 'public', children }) {
  const { status, lastFetchTime } = useHealth();
  const [profileOpen, setProfileOpen] = useState(false);
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const profileRef = useRef(null);
  const location = useLocation();

  // Close profile menu on outside click
  useEffect(() => {
    function handleClick(e) {
      if (profileRef.current && !profileRef.current.contains(e.target)) {
        setProfileOpen(false);
      }
    }
    if (profileOpen) {
      document.addEventListener('mousedown', handleClick);
      return () => document.removeEventListener('mousedown', handleClick);
    }
  }, [profileOpen]);

  // Close both menus on route change
  useEffect(() => {
    setProfileOpen(false);
    setMobileNavOpen(false);
  }, [location.pathname]);

  const isGov = mode === 'government';

  return (
    <header className="global-header" role="banner">
      {/* Left — Brand */}
      <div className="global-header__left">
        <Link to={isGov ? '/government' : '/'} className="global-header__brand" aria-label="Lahore+ home">
          <LPLogo size="sm" />
          <span className="global-header__brand-text">
            <span className="global-header__brand-name">Lahore</span>
            <span className="global-header__brand-plus">+</span>
          </span>
        </Link>
      </div>

      {/* Center — Contextual nav (passed as children) */}
      <nav className={`global-header__center ${mobileNavOpen ? 'global-header__center--open' : ''}`} aria-label={isGov ? 'Government navigation' : 'Main navigation'}>
        {children}
      </nav>

      {/* Mobile hamburger */}
      <button
        className="global-header__hamburger"
        onClick={() => setMobileNavOpen(!mobileNavOpen)}
        aria-label={mobileNavOpen ? 'Close navigation' : 'Open navigation'}
        aria-expanded={mobileNavOpen}
      >
        <span className={`global-header__hamburger-line ${mobileNavOpen ? 'global-header__hamburger-line--open' : ''}`} />
        <span className={`global-header__hamburger-line ${mobileNavOpen ? 'global-header__hamburger-line--open' : ''}`} />
        <span className={`global-header__hamburger-line ${mobileNavOpen ? 'global-header__hamburger-line--open' : ''}`} />
      </button>

      {/* Mobile overlay */}
      {mobileNavOpen && <div className="global-header__overlay" onClick={() => setMobileNavOpen(false)} />}

      {/* Right — Status + Actions */}
      <div className="global-header__right">
        {/* Connection status */}
        <div className="global-header__status" title={STATUS_LABEL[status]}>
          <span className={`status-dot status-dot--${status}`} />
          <span className="global-header__status-text">{STATUS_LABEL[status]}</span>
        </div>

        {/* Notifications bell — navigates to Alerts page */}
        <Link
          to="/alerts"
          className="global-header__icon-btn"
          aria-label="Alerts and notifications"
          title="Alerts and notifications"
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
            <path d="M13.73 21a2 2 0 0 1-3.46 0" />
          </svg>
        </Link>

        {/* Profile menu */}
        <div className="global-header__profile" ref={profileRef}>
          <button
            className="global-header__profile-btn"
            onClick={() => setProfileOpen(!profileOpen)}
            aria-expanded={profileOpen}
            aria-haspopup="true"
            aria-label="Profile menu"
          >
            <span className="global-header__avatar">
              {isGov ? 'G' : 'C'}
            </span>
          </button>

          {profileOpen && (
            <div className="global-header__dropdown" role="menu">
              <div className="global-header__dropdown-header">
                <span className="global-header__dropdown-name">
                  {isGov ? 'Government Console' : 'Citizen View'}
                </span>
                <span className="global-header__dropdown-role">
                  {isGov ? 'Policy Analyst' : 'Public Access'}
                </span>
              </div>
              <div className="global-header__dropdown-divider" />

              <Link
                to="/data-trust"
                className="global-header__dropdown-item global-header__dropdown-item--muted"
                role="menuitem"
                onClick={() => setProfileOpen(false)}
              >
                About Lahore+
              </Link>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
