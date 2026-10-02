/**
 * The spaceport's rocket, redrawn flat from the owner's mark so it holds at 20px:
 * nose, body with fins, three exhaust bars, in whatever colour the text around it is.
 */
export function Logo({ size = 20 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d="M12 1.5C9.4 4.1 8 7.4 7.8 11L12 8l4.2 3C16 7.4 14.6 4.1 12 1.5Z" />
      <path d="M12 9.6 7.75 12.6C5 13.1 3 14.6 2.5 17.5h19c-.5-2.9-2.5-4.4-5.25-4.9Z" />
      <rect x="8" y="18.75" width="2" height="4.5" rx=".5" />
      <rect x="11" y="18.75" width="2" height="4.5" rx=".5" />
      <rect x="14" y="18.75" width="2" height="4.5" rx=".5" />
    </svg>
  )
}
