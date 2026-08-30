/**
 * LoadingState — Clear loading/progress state with contextual skeleton.
 *
 * @param {object} props
 * @param {string} [props.message] - Descriptive loading message
 * @param {string} [props.variant] - Skeleton shape: 'page' | 'hero' | 'forecast' | 'chart' | 'metric'
 * @param {string} [props.context] - Extra context (e.g., 'Your area: DHA') shown below message
 */
export default function LoadingState({
  message = 'Loading forecast data...',
  variant = 'page',
  context = null,
}) {
  return (
    <div
      className="flex flex-col gap-4"
      style={{ padding: 'var(--sp-6)' }}
      role="status"
      aria-live="polite"
      aria-busy="true"
    >
      {/* Status indicator */}
      <div className="flex items-center gap-3">
        <div className="status-dot status-dot--loading" aria-hidden="true" />
        <span className="text-sm" style={{ color: 'var(--slate-600)' }}>
          {message}
        </span>
      </div>

      {context && (
        <div className="type-caption" style={{ color: 'var(--slate-500)', marginTop: '-8px' }}>
          {context}
        </div>
      )}

      {/* Variant-specific skeletons */}
      <div className="skeleton-group" aria-hidden="true">
        {variant === 'hero' && <HeroSkeletonLayout />}
        {variant === 'forecast' && <ForecastSkeletonLayout />}
        {variant === 'chart' && <ChartSkeletonLayout />}
        {variant === 'metric' && <MetricSkeletonLayout />}
        {variant === 'page' && <PageSkeletonLayout />}
      </div>
    </div>
  );
}

/* ── Skeleton Layouts ─────────────────────────────────────── */

function HeroSkeletonLayout() {
  return (
    <div className="skeleton-hero">
      <div className="skeleton skeleton--metric" />
      <div className="skeleton skeleton--heading" style={{ width: '45%' }} />
      <div className="skeleton skeleton--text" style={{ width: '80%' }} />
      <div className="skeleton skeleton--text" style={{ width: '65%' }} />
    </div>
  );
}

function ForecastSkeletonLayout() {
  return (
    <div className="flex gap-3">
      {[1, 2, 3, 4, 5].map(i => (
        <div key={i} className="skeleton skeleton--forecast-card" style={{ flex: 1 }} />
      ))}
    </div>
  );
}

function ChartSkeletonLayout() {
  return (
    <div className="skeleton skeleton--chart" />
  );
}

function MetricSkeletonLayout() {
  return (
    <div className="flex gap-3">
      {[1, 2, 3].map(i => (
        <div key={i} className="skeleton skeleton--metric-card" style={{ flex: 1 }} />
      ))}
    </div>
  );
}

function PageSkeletonLayout() {
  return (
    <div className="flex flex-col gap-3">
      <div className="skeleton skeleton--heading" />
      <div className="flex gap-3">
        {[1, 2, 3, 4, 5].map(i => (
          <div key={i} className="skeleton skeleton--forecast-card" style={{ flex: 1 }} />
        ))}
      </div>
      <div className="skeleton skeleton--card" style={{ height: 200 }} />
    </div>
  );
}
