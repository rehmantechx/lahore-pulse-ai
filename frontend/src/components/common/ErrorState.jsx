/**
 * ErrorState — Backend unavailable, network error, or data errors.
 *
 * Communicates the problem clearly without technical jargon.
 * Provides actionable next steps for the user.
 *
 * @param {object} props
 * @param {Error} props.error - The error object
 * @param {Function} [props.onRetry] - Optional retry callback
 * @param {string} [props.context] - What the user was trying to do (e.g., 'loading forecast')
 * @param {object} [props.cachedData] - Cached/stale data to display with warning
 * @param {string} [props.cachedDataAge] - How old the cached data is (e.g., '2 hours ago')
 */
export default function ErrorState({ error, onRetry, context, cachedData, cachedDataAge }) {
  const isNetwork = error?.name === 'NetworkError' || error?.name === 'TimeoutError';
  const isApiError = error?.name === 'ApiError';
  const is404 = error?.status === 404;
  const is429 = error?.status === 429;

  let title = 'Something went wrong';
  let description = 'An unexpected error occurred while loading data.';
  let suggestion = '';
  let icon = '⚠️';

  if (isNetwork) {
    title = 'Cannot reach the server';
    description = 'The backend service may not be running.';
    suggestion = 'Try refreshing the page. If this persists, the service may be temporarily down.';
    icon = '🔌';
  } else if (is404) {
    title = 'Data not found';
    description = 'The information you are looking for is not available yet.';
    suggestion = 'This can happen if no air quality readings have been collected for this time period.';
    icon = '📭';
  } else if (is429) {
    title = 'Too many requests';
    description = 'The server is processing too many requests right now.';
    suggestion = 'Please wait a moment and try again.';
    icon = '⏳';
  } else if (isApiError) {
    title = 'Service unavailable';
    description = error.message || 'The forecast service returned an error.';
    suggestion = 'This is usually temporary. Try again in a few minutes.';
    icon = '🔧';
  }

  return (
    <div className="error-state" role="alert">
      <div className="error-state__header">
        <span className="error-state__icon" aria-hidden="true">{icon}</span>
        <div>
          <div className="error-state__title">{title}</div>
          <div className="error-state__description">{description}</div>
        </div>
      </div>

      {context && (
        <div className="error-state__context">
          While {context}
        </div>
      )}

      {suggestion && (
        <div className="error-state__suggestion">
          {suggestion}
        </div>
      )}

      {cachedData && cachedDataAge && (
        <div className="error-state__cached">
          <div className="error-state__cached-header">
            📋 Showing data from {cachedDataAge} (may be outdated)
          </div>
          {cachedData}
        </div>
      )}

      <div className="error-state__actions">
        {onRetry && (
          <button className="btn" onClick={onRetry}>
            Try again
          </button>
        )}
        <button
          className="btn btn--secondary"
          onClick={() => window.location.reload()}
        >
          Refresh page
        </button>
      </div>
    </div>
  );
}
