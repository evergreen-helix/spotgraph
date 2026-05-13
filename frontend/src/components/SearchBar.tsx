import { forwardRef } from "react";

interface Props {
  value: string;
  onChange: (v: string) => void;
  onSubmit: () => void;
  isOpen: boolean;
}

const SearchBar = forwardRef<HTMLInputElement, Props>(function SearchBar(
  { value, onChange, onSubmit, isOpen },
  ref
) {
  return (
    <div className={`bar ${isOpen ? "open" : ""}`}>
      <svg
        className="lens"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth={2}
      >
        <circle cx="11" cy="11" r="7" />
        <path d="m20 20-3.5-3.5" />
      </svg>
      <input
        ref={ref}
        type="text"
        value={value}
        placeholder="Try: where should I eat?"
        autoComplete="off"
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter") onSubmit();
        }}
      />
      <button className="go" onClick={onSubmit}>
        Search
      </button>
    </div>
  );
});

export default SearchBar;
