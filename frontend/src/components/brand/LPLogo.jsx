/**
 * LPLogo — Lahore+ premium civic-tech mark.
 *
 * Deep teal background with white L + teal accent crossbar.
 * Clean, distinctive, works at all sizes.
 * Renders inline SVG for crisp scaling.
 *
 * @param {object} props
 * @param {'sm'|'md'|'lg'} props.size - Output size
 * @param {string} props.className - Optional additional class
 */
export default function LPLogo({ size = 'md', className = '' }) {
  const sizes = { sm: 24, md: 32, lg: 48 };
  const px = sizes[size] || sizes.md;

  return (
    <svg
      width={px}
      height={px}
      viewBox="0 0 48 48"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={`lp-logo ${className}`}
      aria-label="Lahore+ logo"
      role="img"
    >
      {/* Background — Deep teal (brand primary) */}
      <rect width="48" height="48" rx="8" fill="#134E4A" />

      {/* Geometric L — architectural, bold */}
      <path
        d="M11 11 L11 37 L29 37"
        stroke="#FFFFFF"
        strokeWidth="5"
        strokeLinecap="square"
        strokeLinejoin="miter"
        fill="none"
      />

      {/* Accent + crossbar — integrated into L, signals intelligence */}
      <path
        d="M18 18 L30 18"
        stroke="#5EEAD4"
        strokeWidth="3"
        strokeLinecap="round"
        fill="none"
      />
      <path
        d="M24 12 L24 24"
        stroke="#5EEAD4"
        strokeWidth="3"
        strokeLinecap="round"
        fill="none"
      />
    </svg>
  );
}
