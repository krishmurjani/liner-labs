interface Props {
  value: string
  onChange: (value: string) => void
  disabled?: boolean
}

export function SearchBar({ value, onChange, disabled }: Props) {
  return (
    <div className="relative">
      <input
        type="text"
        value={value}
        onChange={e => onChange(e.target.value)}
        disabled={disabled}
        placeholder="Search lyrics or a phrase…"
        className="w-full bg-zinc-900 border border-zinc-700 rounded-xl px-4 py-3 pr-10
                   text-zinc-100 placeholder-zinc-500 text-base
                   focus:outline-none focus:border-zinc-400
                   disabled:opacity-40 disabled:cursor-not-allowed
                   transition-colors"
        autoFocus
      />
      {value && (
        <button
          onClick={() => onChange('')}
          className="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-500
                     hover:text-zinc-300 transition-colors text-lg leading-none"
          aria-label="Clear search"
        >
          ×
        </button>
      )}
    </div>
  )
}
