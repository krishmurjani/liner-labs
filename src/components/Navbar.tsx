import { Link } from 'react-router-dom'
import { ThemeToggle } from './ThemeToggle'

interface Props {
  theme: 'dark' | 'light'
  onToggle: () => void
}

export function Navbar({ theme, onToggle }: Props) {
  return (
    <header className="sticky top-0 z-50 w-full
                       bg-white/80 dark:bg-zinc-950/80
                       backdrop-blur-md
                       border-b border-zinc-200 dark:border-zinc-800">
      <div className="max-w-3xl mx-auto px-4 h-14 flex items-center justify-between">
        <Link
          to="/"
          className="flex items-center gap-2.5 hover:opacity-70 transition-opacity"
        >
          {/* Vinyl record logo */}
          <svg width="26" height="26" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
            <circle cx="16" cy="16" r="15" fill="#18181b"/>
            <circle cx="16" cy="16" r="12" fill="none" stroke="#3f3f46" strokeWidth="0.75"/>
            <circle cx="16" cy="16" r="9.5" fill="none" stroke="#3f3f46" strokeWidth="0.75"/>
            <circle cx="16" cy="16" r="7" fill="none" stroke="#3f3f46" strokeWidth="0.75"/>
            <circle cx="16" cy="16" r="4.5" fill="#a78bfa"/>
            <circle cx="16" cy="16" r="1.2" fill="#18181b"/>
            <path d="M 6 10 A 11 11 0 0 1 26 10" stroke="white" strokeWidth="1" strokeLinecap="round" opacity="0.15"/>
          </svg>
          <span className="text-base font-bold tracking-tight text-zinc-900 dark:text-white">
            Liner Labs
          </span>
        </Link>
        <ThemeToggle theme={theme} onToggle={onToggle} />
      </div>
    </header>
  )
}
