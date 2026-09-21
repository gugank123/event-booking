import { useEffect, useState } from 'react';
import { api } from '../api/client';
import { useAuth } from '../context/AuthContext';
import { formatDate } from '../utils/format';
import { StarInput, Stars } from './Stars';

export default function Reviews({ eventId }) {
  const { user, token } = useAuth();
  const [reviews, setReviews] = useState([]);
  const [rating, setRating] = useState(5);
  const [comment, setComment] = useState('');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  function load() {
    api
      .get(`/events/${eventId}/reviews/`)
      .then((data) => setReviews(data.reviews))
      .catch(() => {});
  }

  useEffect(load, [eventId]);

  async function handleSubmit(e) {
    e.preventDefault();
    setError('');
    setSubmitting(true);
    try {
      await api.post(`/events/${eventId}/reviews/`, { rating, comment }, token);
      setComment('');
      load();
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDelete(id) {
    if (!window.confirm('Delete this review?')) return;
    try {
      await api.del(`/events/reviews/${id}/`, token);
      load();
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <section className="reviews">
      <h2>Reviews {reviews.length > 0 && `(${reviews.length})`}</h2>
      {user ? (
        <form className="review-form" onSubmit={handleSubmit}>
          <StarInput value={rating} onChange={setRating} />
          <div className="form" style={{ border: 'none', padding: 0, background: 'none', marginTop: '0.75rem' }}>
            <textarea
              placeholder="What did you think? (optional)"
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              rows={3}
            />
          </div>
          {error && <p className="form-error">{error}</p>}
          <button className="btn btn--primary" type="submit" disabled={submitting} style={{ marginTop: '0.75rem' }}>
            {submitting ? 'Posting…' : 'Post review'}
          </button>
        </form>
      ) : (
        <p className="muted">Sign in to leave a review.</p>
      )}
      {reviews.length === 0 ? (
        <p className="muted">No reviews yet — be the first.</p>
      ) : (
        reviews.map((r) => (
          <div key={r.id} className="review">
            <div className="review__head">
              <span className="review__author">{r.author_name}</span>
              <Stars value={r.rating} />
              <span className="review__date">{formatDate(r.created_at)}</span>
            </div>
            {r.comment && <p>{r.comment}</p>}
            {(r.mine || user?.role === 'admin') && (
              <button className="btn btn--ghost btn--sm" style={{ marginTop: '0.5rem' }} onClick={() => handleDelete(r.id)}>
                Delete
              </button>
            )}
          </div>
        ))
      )}
    </section>
  );
}
