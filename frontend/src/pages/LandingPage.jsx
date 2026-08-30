/**
 * LandingPage — Premium cinematic entry experience for Lahore+.
 *
 * A full editorial city-platform landing page:
 *   • Cinematic hero with Lahore landmark imagery
 *   • Heritage / landmark visual storytelling
 *   • "The City in One Place" platform showcase
 *   • Citizen / Government dual-path entry
 *   • Live city moment (real data)
 *   • City map preview
 *
 * Architecture preserved: /citizen (public) + /government (authenticated).
 * No fake data. No dead buttons. No backend changes.
 */

import { useState, useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext.jsx';
import { useHealth } from '../hooks/useHealth.js';
import {
  Shield, Map, ArrowRight, Wind, AlertTriangle, Eye,
  BarChart3, Bookmark, Clock, ChevronDown, Building2,
  Landmark, Compass, Activity
} from 'lucide-react';
import ProductNarrative from '../components/landing/ProductNarrative';

/* ─────────────────────────────────────────────────────────
   Scroll-reveal hook — lightweight IntersectionObserver
   ───────────────────────────────────────────────────────── */
function useReveal(threshold = 0.15) {
  const ref = useRef(null);
  const [visible, setVisible] = useState(false);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (prefersReduced) { setVisible(true); return; }
    const io = new IntersectionObserver(
      ([entry]) => { if (entry.isIntersecting) { setVisible(true); io.disconnect(); } },
      { threshold }
    );
    io.observe(el);
    return () => io.disconnect();
  }, [threshold]);
  return [ref, visible];
}

/* ─────────────────────────────────────────────────────────
   Parallax hook — tracks scroll offset for a section
   ───────────────────────────────────────────────────────── */
function useParallax(speed = 0.3) {
  const ref = useRef(null);
  const [offset, setOffset] = useState(0);
  useEffect(() => {
    const prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (prefersReduced) return;
    let ticking = false;
    function onScroll() {
      if (ticking) return;
      ticking = true;
      requestAnimationFrame(() => {
        if (!ref.current) { ticking = false; return; }
        const rect = ref.current.getBoundingClientRect();
        const center = rect.top + rect.height / 2;
        const viewCenter = window.innerHeight / 2;
        setOffset((center - viewCenter) * speed);
        ticking = false;
      });
    }
    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();
    return () => window.removeEventListener('scroll', onScroll);
  }, [speed]);
  return [ref, offset];
}

/* ═════════════════════════════════════════════════════════
   Lahore landmark image definitions (Unsplash sources)
   ═════════════════════════════════════════════════════════ */
const HERO_IMAGE = 'https://images.unsplash.com/photo-1713271523270-af8dc2425345?w=1920&q=80&auto=format&fit=crop';
const HERO_IMAGE_FALLBACK = '/lahore-hero-fallback.svg';

/* Local SVG fallbacks for landmarks when Unsplash images are blocked */
const LANDMARK_FALLBACKS = {
  'Minar-e-Pakistan': '/landmarks/minar-e-pakistan.svg',
  'Badshahi Mosque': '/landmarks/badshahi-mosque.svg',
  'Lahore Fort': '/landmarks/lahore-fort.svg',
  'Wazir Khan Mosque': '/landmarks/wazir-khan-mosque.svg',
};

const LANDMARKS = [
  {
    name: 'Minar-e-Pakistan',
    desc: 'The tower where Pakistan was born — a symbol of self-determination standing in Iqbal Park.',
    image: '/landmarks/minar-e-pakistan-v2.jpg',
    year: '1960–1968',
  },
  {
    name: 'Badshahi Mosque',
    desc: 'Built in 1673 by Emperor Aurangzeb — one of the largest Mughal-era mosques in the world.',
    image: 'https://images.unsplash.com/photo-1599079027267-7d0cea474b07?w=800&q=80&auto=format&fit=crop',
    year: '1673',
  },
  {
    name: 'Lahore Fort',
    desc: 'A UNESCO World Heritage Site — the heart of Mughal Lahore, rebuilt by Emperor Akbar in 1566 on ancient foundations.',
    image: 'https://images.unsplash.com/photo-1722953035409-25a166808276?w=800&q=80&auto=format&fit=crop',
    year: '1566 CE',
  },
  {
    name: 'Wazir Khan Mosque',
    desc: 'Famed for its intricate kashi-kari tilework — one of the most ornately decorated mosques in the world.',
    image: 'https://images.unsplash.com/photo-1606672972031-79e99438f6d4?w=800&q=80&auto=format&fit=crop',
    year: '1634–1641',
  },
];

/* Citizen capabilities */
const CAPABILITIES = [
  { icon: Activity, label: 'Air Quality', desc: 'Check conditions.', to: '/air-quality' },
  { icon: Map, label: 'City Map', desc: "See what's happening nearby.", to: '/city-map' },
  { icon: AlertTriangle, label: 'Alerts', desc: 'Get important alerts.', to: '/alerts' },
  { icon: BarChart3, label: 'Insights', desc: 'Understand your city.', to: '/insights' },
  { icon: Eye, label: 'Reports', desc: 'Detailed analysis and trends.', to: '/reports' },
  { icon: Bookmark, label: 'Favorites', desc: 'Save the places that matter.', to: '/my-lahore' },
];

/* ═════════════════════════════════════════════════════════
   Image with local fallback — handles Unsplash ORB blocks
   ═════════════════════════════════════════════════════════ */
function LandmarkImage({ src, alt, name, className }) {
  const [error, setError] = useState(false);
  const fallback = LANDMARK_FALLBACKS[name];
  if (error && fallback) {
    return <img src={fallback} alt={alt} className={className} loading="lazy" />;
  }
  return <img src={src} alt={alt} className={className} loading="lazy" onError={() => setError(true)} />;
}

/* ═════════════════════════════════════════════════════════
   Landing Header — transparent → solid on scroll
   ═════════════════════════════════════════════════════════ */
function LandingHeader({ scrolled }) {
  const { isAuthenticated, isGovernment } = useAuth();
  return (
    <header className={`lp-header ${scrolled ? 'lp-header--solid' : ''}`}>
      <div className="lp-header__inner">
        <Link to="/" className="lp-header__brand" aria-label="Lahore+ home">
          <span className="lp-header__logo">
            <Building2 size={22} strokeWidth={1.5} />
          </span>
          <span className="lp-header__brand-text">
            <span className="lp-header__brand-name">Lahore</span>
            <span className="lp-header__brand-plus">+</span>
          </span>
        </Link>
        <nav className="lp-header__nav" aria-label="Landing navigation">
          <Link to="/citizen" className="lp-header__link">Citizen Access</Link>
          <Link to="/data-trust" className="lp-header__link">How It Works</Link>
          {isAuthenticated && isGovernment ? (
            <Link to="/government" className="lp-header__link lp-header__link--gov">
              <Shield size={14} strokeWidth={2} /> Command Center
            </Link>
          ) : (
            <Link to="/login" className="lp-header__link lp-header__link--gov">
              <Shield size={14} strokeWidth={2} /> Sign In
            </Link>
          )}
        </nav>
      </div>
    </header>
  );
}

/* ═════════════════════════════════════════════════════════
   SECTION 1 — Cinematic Hero
   ═════════════════════════════════════════════════════════ */
function HeroSection() {
  const [parallaxRef, pOffset] = useParallax(0.25);
  const { isAuthenticated, isGovernment } = useAuth();
  const [imgLoaded, setImgLoaded] = useState(false);
  const [imgError, setImgError] = useState(false);

  return (
    <section className="lp-hero" ref={parallaxRef}>
      {/* Background image layer with parallax */}
      <div
        className="lp-hero__bg"
        style={{ transform: `translateY(${pOffset}px)` }}
        aria-hidden="true"
      >
        {!imgError ? (
          <img
            src={HERO_IMAGE}
            alt=""
            className={`lp-hero__bg-img ${imgLoaded ? 'lp-hero__bg-img--loaded' : ''}`}
            loading="eager"
            onLoad={() => setImgLoaded(true)}
            onError={() => setImgError(true)}
          />
        ) : (
          <div className="lp-hero__bg-fallback" style={{ backgroundImage: `url(${HERO_IMAGE_FALLBACK})` }} />
        )}
        <div className="lp-hero__bg-overlay" />
      </div>

      {/* Content */}
      <div className="lp-hero__content">
        <div className="lp-hero__badge">Punjab Digital Platform</div>
        <h1 className="lp-hero__title">
          Lahore<span className="lp-hero__title-plus">+</span>
        </h1>
        <p className="lp-hero__tagline">Predictions with receipts.</p>
        <p className="lp-hero__desc">
          See what's happening across Lahore, stay informed,
          and access the city's digital services.
        </p>
        <div className="lp-hero__actions">
          <Link to="/citizen" className="lp-hero__btn lp-hero__btn--primary">
            Explore Lahore <ArrowRight size={18} />
          </Link>
          {isAuthenticated && isGovernment ? (
            <Link to="/government" className="lp-hero__btn lp-hero__btn--secondary">
              <Shield size={16} /> Command Center
            </Link>
          ) : (
            <Link to="/login" className="lp-hero__btn lp-hero__btn--secondary">
              <Shield size={16} /> Government Access
            </Link>
          )}
        </div>
        <div className="lp-hero__scroll-hint" aria-hidden="true">
          <ChevronDown size={20} />
        </div>
      </div>
    </section>
  );
}

/* ═════════════════════════════════════════════════════════
   SECTION 2 — Heritage / Landmarks (editorial collage)
   ═════════════════════════════════════════════════════════ */
function HeritageSection() {
  const [headerRef, headerVis] = useReveal(0.1);
  const [gridRef, gridVis] = useReveal(0.05);

  return (
    <section className="lp-heritage">
      <div className="lp-heritage__header" ref={headerRef}>
        <div className={`lp-reveal ${headerVis ? 'lp-reveal--visible' : ''}`}>
          <span className="lp-section-label">Heritage</span>
          <h2 className="lp-heritage__title">A city of a thousand years</h2>
          <p className="lp-heritage__subtitle">
            Lahore's story spans empires, revolutions, and reinventions.
            Lahore+ carries that legacy into the digital age.
          </p>
        </div>
      </div>

      <div className="lp-heritage__grid" ref={gridRef}>
        {/* Large primary landmark */}
        {LANDMARKS.slice(0, 1).map((lm) => (
          <div
            key={lm.name}
            className={`lp-heritage__item lp-heritage__item--large ${gridVis ? 'lp-reveal--visible' : ''}`}
          >
            <div className="lp-heritage__img-wrap">
              <LandmarkImage src={lm.image} alt={lm.name} name={lm.name} className="lp-heritage__img" />
              <div className="lp-heritage__img-overlay" />
            </div>
            <div className="lp-heritage__item-content">
              <span className="lp-heritage__year">{lm.year}</span>
              <h3 className="lp-heritage__item-title">{lm.name}</h3>
              <p className="lp-heritage__item-desc">{lm.desc}</p>
            </div>
          </div>
        ))}

        {/* Smaller landmarks grid */}
        <div className="lp-heritage__small-grid">
          {LANDMARKS.slice(1).map((lm, i) => (
            <div
              key={lm.name}
              className={`lp-heritage__item lp-heritage__item--small ${gridVis ? 'lp-reveal--visible' : ''}`}
              style={{ transitionDelay: `${(i + 1) * 0.1}s` }}
            >
              <div className="lp-heritage__img-wrap">
                <LandmarkImage src={lm.image} alt={lm.name} name={lm.name} className="lp-heritage__img" />
                <div className="lp-heritage__img-overlay" />
              </div>
              <div className="lp-heritage__item-content">
                <span className="lp-heritage__year">{lm.year}</span>
                <h3 className="lp-heritage__item-title">{lm.name}</h3>
                <p className="lp-heritage__item-desc">{lm.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ═════════════════════════════════════════════════════════
   SECTION 3 — The City in One Place
   ═════════════════════════════════════════════════════════ */
function CityPlatformSection() {
  const [ref, visible] = useReveal(0.05);
  const [activeCap, setActiveCap] = useState(0);

  return (
    <section className="lp-platform" ref={ref}>
      <div className={`lp-reveal ${visible ? 'lp-reveal--visible' : ''}`}>
        <span className="lp-section-label">Platform</span>
        <h2 className="lp-platform__title">The city in one place</h2>
        <p className="lp-platform__subtitle">
          Lahore+ brings together everything you need to understand
          and navigate your city's air quality — all in a single platform.
        </p>
      </div>

      <div className="lp-platform__grid">
        {CAPABILITIES.map((cap, i) => {
          const Icon = cap.icon;
          return (
            <Link
              key={cap.label}
              to={cap.to}
              className={`lp-platform__item ${visible ? 'lp-reveal--visible' : ''} ${activeCap === i ? 'lp-platform__item--active' : ''}`}
              style={{ transitionDelay: `${i * 0.08}s` }}
              onMouseEnter={() => setActiveCap(i)}
              onFocus={() => setActiveCap(i)}
            >
              <div className="lp-platform__item-icon">
                <Icon size={22} strokeWidth={1.5} />
              </div>
              <h3 className="lp-platform__item-label">{cap.label}</h3>
              <p className="lp-platform__item-desc">{cap.desc}</p>
              <span className="lp-platform__item-link">
                Open <ArrowRight size={14} />
              </span>
            </Link>
          );
        })}
      </div>
    </section>
  );
}

/* ═════════════════════════════════════════════════════════
   SECTION 4 — Citizen / Government Dual Path
   ═════════════════════════════════════════════════════════ */
function DualPathSection() {
  const [ref, visible] = useReveal(0.1);
  const { isAuthenticated, isGovernment } = useAuth();

  return (
    <section className="lp-dual" ref={ref}>
      <div className={`lp-reveal ${visible ? 'lp-reveal--visible' : ''}`}>
        <span className="lp-section-label">Access</span>
        <h2 className="lp-dual__title">Two experiences. One city.</h2>
      </div>

      <div className="lp-dual__grid">
        {/* Citizen */}
        <div className={`lp-dual__card lp-dual__card--citizen ${visible ? 'lp-reveal--visible' : ''}`} style={{ transitionDelay: '0.1s' }}>
          <div className="lp-dual__card-accent lp-dual__card-accent--citizen" />
          <div className="lp-dual__card-content">
            <span className="lp-dual__card-label">Citizen</span>
            <h3 className="lp-dual__card-title">Everything you need<br />to understand Lahore.</h3>
            <p className="lp-dual__card-desc">
              Real-time air quality data, forecasts, city maps,
              alerts, and health guidance — designed for everyone.
            </p>
            <ul className="lp-dual__card-features">
              <li>Air quality &amp; forecasts</li>
              <li>Interactive city map</li>
              <li>Health alerts &amp; guidance</li>
              <li>Saved locations</li>
            </ul>
            <Link to="/citizen" className="lp-dual__card-btn lp-dual__card-btn--citizen">
              Explore Lahore <ArrowRight size={16} />
            </Link>
          </div>
        </div>

        {/* Government */}
        <div className={`lp-dual__card lp-dual__card--gov ${visible ? 'lp-reveal--visible' : ''}`} style={{ transitionDelay: '0.2s' }}>
          <div className="lp-dual__card-accent lp-dual__card-accent--gov" />
          <div className="lp-dual__card-content">
            <span className="lp-dual__card-label">
              <Shield size={12} /> Secure Access
            </span>
            <h3 className="lp-dual__card-title">Operational intelligence<br />for government teams.</h3>
            <p className="lp-dual__card-desc">
              Authorized government operators access the Command Center
              for incident monitoring, trajectory analysis, and response coordination.
            </p>
            <ul className="lp-dual__card-features">
              <li>Incident detection</li>
              <li>Forecast trajectory analysis</li>
              <li>Historical analog engine</li>
              <li>Investigation tools</li>
            </ul>
            {isAuthenticated && isGovernment ? (
              <Link to="/government" className="lp-dual__card-btn lp-dual__card-btn--gov">
                Open Command Center <ArrowRight size={16} />
              </Link>
            ) : (
              <Link to="/login" className="lp-dual__card-btn lp-dual__card-btn--gov">
                Sign In to Command Center <ArrowRight size={16} />
              </Link>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}

/* ═════════════════════════════════════════════════════════
   SECTION 5 — Live City Moment (real data)
   ═════════════════════════════════════════════════════════ */
function LiveCitySection() {
  const [ref, visible] = useReveal(0.1);
  const { status } = useHealth();
  const [time, setTime] = useState('');

  useEffect(() => {
    function updateTime() {
      try {
        setTime(new Date().toLocaleTimeString('en-PK', {
          hour: '2-digit', minute: '2-digit', timeZone: 'Asia/Karachi',
        }));
      } catch { setTime(''); }
    }
    updateTime();
    const id = setInterval(updateTime, 60000);
    return () => clearInterval(id);
  }, []);

  const isOnline = status === 'online';

  return (
    <section className="lp-live" ref={ref}>
      <div className={`lp-live__inner ${visible ? 'lp-reveal--visible' : ''}`}>
        <div className="lp-live__left">
          <span className="lp-section-label">Live</span>
          <h2 className="lp-live__title">A city that never sleeps</h2>
          <p className="lp-live__desc">
            Lahore+ monitors conditions across the city in real time.
            This is the live digital pulse of Lahore.
          </p>
        </div>
        <div className="lp-live__indicators">
          <div className="lp-live__indicator">
            <Clock size={16} strokeWidth={1.5} />
            <span className="lp-live__indicator-label">Lahore Time</span>
            <span className="lp-live__indicator-value">{time || '—'}</span>
          </div>
          <div className="lp-live__indicator">
            <Activity size={16} strokeWidth={1.5} />
            <span className="lp-live__indicator-label">Platform Status</span>
            <span className={`lp-live__indicator-value ${isOnline ? 'lp-live__indicator-value--ok' : ''}`}>
              {isOnline ? 'Online' : 'Offline'}
            </span>
          </div>
          <div className="lp-live__indicator">
            <Wind size={16} strokeWidth={1.5} />
            <span className="lp-live__indicator-label">Air Quality</span>
            <span className="lp-live__indicator-value">Live monitoring</span>
          </div>
          <div className="lp-live__indicator">
            <Compass size={16} strokeWidth={1.5} />
            <span className="lp-live__indicator-label">Coverage</span>
            <span className="lp-live__indicator-value">All stations</span>
          </div>
        </div>
      </div>
      <div className="lp-live__map-cta">
        <Link to="/city-map" className="lp-live__map-link">
          <Map size={16} /> Open City Map <ArrowRight size={14} />
        </Link>
      </div>
    </section>
  );
}

/* ═════════════════════════════════════════════════════════
   SECTION 6 — Premium Footer
   ═════════════════════════════════════════════════════════ */
function LandingFooter() {
  return (
    <footer className="lp-footer">
      <div className="lp-footer__inner">
        <div className="lp-footer__brand">
          <Building2 size={18} strokeWidth={1.5} />
          <span>Lahore<span className="lp-footer__plus">+</span></span>
        </div>
        <p className="lp-footer__desc">
          A public digital platform for air quality information in Lahore, Punjab.
        </p>
        <div className="lp-footer__links">
          <Link to="/citizen" className="lp-footer__link">Citizen Access</Link>
          <span className="lp-footer__sep">|</span>
          <Link to="/data-trust" className="lp-footer__link">How It Works</Link>
          <span className="lp-footer__sep">|</span>
          <Link to="/login" className="lp-footer__link">Government Access</Link>
        </div>
        <p className="lp-footer__copy">
          &copy; {new Date().getFullYear()} Lahore+ &middot; Punjab Digital Platform
        </p>
      </div>
    </footer>
  );
}

/* ═════════════════════════════════════════════════════════
   MAIN LANDING PAGE
   ═════════════════════════════════════════════════════════ */
export default function LandingPage() {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    function onScroll() {
      setScrolled(window.scrollY > 60);
    }
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  return (
    <div className="lp-landing">
      <LandingHeader scrolled={scrolled} />
      <HeroSection />
      <HeritageSection />
      <ProductNarrative />
      <CityPlatformSection />
      <DualPathSection />
      <LiveCitySection />
      <LandingFooter />
    </div>
  );
}
