export function Stars({ value, max = 5 }) {
  if (value == null) return <span className="muted">No ratings yet</span>;
  const filled = Math.round(value);
  return (
    <span className="stars" aria-label={`${value} out of ${max} stars`}>
      {Array.from({ length: max }, (_, i) => (
        <span key={i} className={`star ${i < filled ? 'is-filled' : ''}`}>
          ★
        </span>
      ))}
      <span>&nbsp;{Number(value).toFixed(1)}</span>
    </span>
  );
}

export function StarInput({ value, onChange }) {
  return (
    <span className="star-input" role="radiogroup" aria-label="Your rating">
      {[1, 2, 3, 4, 5].map((n) => (
        <button
          key={n}
          type="button"
          className={`star ${n <= value ? 'is-filled' : ''}`}
          onClick={() => onChange(n)}
          aria-label={`${n} star${n > 1 ? 's' : ''}`}
        >
          ★
        </button>
      ))}
    </span>
  );
}
