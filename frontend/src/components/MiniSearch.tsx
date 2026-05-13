interface Props {
  show: boolean;
  query: string;
  onExpand: () => void;
}

export default function MiniSearch({ show, query, onExpand }: Props) {
  return (
    <div className={`mini-search ${show ? "show" : ""}`} onClick={onExpand}>
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
        <circle cx="11" cy="11" r="7" />
        <path d="m20 20-3.5-3.5" />
      </svg>
      <span>search</span>
      {query.trim() && <span className="mini-query">"{query}"</span>}
    </div>
  );
}
