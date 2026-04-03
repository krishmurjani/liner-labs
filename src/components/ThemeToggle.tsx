import { useRef } from 'react'

interface Props {
  theme: 'dark' | 'light'
  onToggle: () => void
}

function SunIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="4" />
      <line x1="12" y1="2" x2="12" y2="6" />
      <line x1="12" y1="18" x2="12" y2="22" />
      <line x1="4.22" y1="4.22" x2="7.05" y2="7.05" />
      <line x1="16.95" y1="16.95" x2="19.78" y2="19.78" />
      <line x1="2" y1="12" x2="6" y2="12" />
      <line x1="18" y1="12" x2="22" y2="12" />
      <line x1="4.22" y1="19.78" x2="7.05" y2="16.95" />
      <line x1="16.95" y1="7.05" x2="19.78" y2="4.22" />
    </svg>
  )
}

function MoonIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
    </svg>
  )
}

export function ThemeToggle({ theme, onToggle }: Props) {
  const btnRef = useRef<HTMLButtonElement>(null)

  const handleClick = () => {
    if (btnRef.current) {
      const rect = btnRef.current.getBoundingClientRect()
      document.documentElement.style.setProperty('--reveal-x', `${rect.left + rect.width / 2}px`)
      document.documentElement.style.setProperty('--reveal-y', `${rect.top + rect.height / 2}px`)
    }

    // View Transitions API — falls back to instant toggle if unsupported
    if (!(document as any).startViewTransition) {
      onToggle()
      return
    }
    ;(document as any).startViewTransition(onToggle)
  }

  return (
    <button
      ref={btnRef}
      onClick={handleClick}
      aria-label={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
      className="p-2 rounded-full text-zinc-400 hover:text-zinc-200 dark:text-zinc-500
                 dark:hover:text-zinc-300 hover:bg-zinc-800 dark:hover:bg-zinc-800
                 transition-colors duration-150"
    >
      {theme === 'dark' ? <SunIcon /> : <MoonIcon />}
    </button>
  )
}
