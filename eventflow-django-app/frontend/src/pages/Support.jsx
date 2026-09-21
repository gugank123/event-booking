import { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { api } from '../api/client';
import { useAuth } from '../context/AuthContext';
import { formatDate } from '../utils/format';

const TICKET_CATEGORIES = [
  'booking', 'tickets', 'seats', 'payments', 'cancellation',
  'refunds', 'account', 'events', 'organizer', 'technical', 'other'
];

const REPORT_CATEGORIES = ['event', 'organizer', 'booking', 'payment', 'technical', 'other'];

export default function Support() {
  const { token } = useAuth();
  const [searchParams] = useSearchParams();
  const [tab, setTab] = useState(searchParams.get('tab') === 'report' ? 'report' : 'tickets');
  const [tickets, setTickets] = useState([]);
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [ok, setOk] = useState('');

  const [subject, setSubject] = useState('');
  const [ticketCategory, setTicketCategory] = useState('booking');
  const [description, setDescription] = useState('');
  const [priority, setPriority] = useState('MEDIUM');

  const [reportCategory, setReportCategory] = useState('event');
  const [reportSubject, setReportSubject] = useState('');
  const [reportDescription, setReportDescription] = useState('');

  function load() {
    setLoading(true);
    Promise.all([api.get('/comms/support/', token), api.get('/comms/reports/', token)])
      .then(([t, r]) => {
        setTickets(t.tickets);
        setReports(r.reports);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }

  useEffect(load, [token]);

  async function handleTicket(e) {
    e.preventDefault();
    setError('');
    setOk('');
    try {
      const data = await api.post(
        '/comms/support/',
        { subject, category: ticketCategory, description, priority },
        token
      );
      setSubject('');
      setDescription('');
      setOk(`Ticket #${data.ticket.id} opened — we'll reply by email and here.`);
      load();
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleReport(e) {
    e.preventDefault();
    setError('');
    setOk('');
    try {
      const data = await api.post(
        '/comms/reports/',
        { category: reportCategory, subject: reportSubject, description: reportDescription },
        token
      );
      setReportSubject('');
      setReportDescription('');
      setOk(`Report #${data.report.id} filed — thank you.`);
      load();
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div className="page page--narrow">
      <h1>Customer care</h1>
      <div className="filter-row">
        {[
          ['tickets', 'My tickets'],
          ['new', 'New ticket'],
          ['report', 'Report a problem']
        ].map(([v, label]) => (
          <button key={v} className={`chip ${tab === v ? 'is-active' : ''}`} onClick={() => setTab(v)}>
            {label}
          </button>
        ))}
      </div>

      {error && <p className="form-error">{error}</p>}
      {ok && <p className="form-ok">{ok}</p>}

      {tab === 'tickets' &&
        (loading ? (
          <p className="muted">Loading…</p>
        ) : tickets.length === 0 ? (
          <div className="empty-state">
            <h3>No support tickets.</h3>
            <p>Open one any time — we reply here and by email.</p>
          </div>
        ) : (
          <div className="ticket-list">
            {tickets.map((t) => (
              <Link key={t.id} to={`/support/${t.id}`} className="conversation-row">
                <div>
                  <h3>
                    #{t.id} · {t.subject}
                  </h3>
                  <p className="muted">
                    {t.category} · {t.reply_count} replies · {formatDate(t.updated_at)}
                  </p>
                </div>
                <span className={`status-pill status-pill--${t.status === 'OPEN' ? 'published' : t.status === 'CLOSED' || t.status === 'RESOLVED' ? 'cancelled' : 'draft'}`}>
                  {t.status.replace(/_/g, ' ')}
                </span>
              </Link>
            ))}
          </div>
        ))}

      {tab === 'new' && (
        <form className="form" onSubmit={handleTicket}>
          <label>
            Subject
            <input required value={subject} onChange={(e) => setSubject(e.target.value)} maxLength={200} />
          </label>
          <div className="form-row">
            <label>
              Category
              <select value={ticketCategory} onChange={(e) => setTicketCategory(e.target.value)}>
                {TICKET_CATEGORIES.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Priority
              <select value={priority} onChange={(e) => setPriority(e.target.value)}>
                {['LOW', 'MEDIUM', 'HIGH', 'URGENT'].map((p) => (
                  <option key={p} value={p}>
                    {p}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <label>
            Description
            <textarea required value={description} onChange={(e) => setDescription(e.target.value)} rows={5} />
          </label>
          <button className="btn btn--primary" type="submit">
            Open ticket
          </button>
        </form>
      )}

      {tab === 'report' && (
        <>
          <form className="form" onSubmit={handleReport}>
            <label>
              Category
              <select value={reportCategory} onChange={(e) => setReportCategory(e.target.value)}>
                {REPORT_CATEGORIES.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Subject
              <input required value={reportSubject} onChange={(e) => setReportSubject(e.target.value)} maxLength={200} />
            </label>
            <label>
              What happened?
              <textarea required value={reportDescription} onChange={(e) => setReportDescription(e.target.value)} rows={5} />
            </label>
            <button className="btn btn--primary" type="submit">
              File report
            </button>
          </form>
          {reports.length > 0 && (
            <>
              <h2>My reports</h2>
              <div className="ticket-list">
                {reports.map((r) => (
                  <div key={r.id} className="conversation-row">
                    <div>
                      <h3>
                        #{r.id} · {r.subject}
                      </h3>
                      <p className="muted">
                        {r.category} · {formatDate(r.created_at)}
                      </p>
                    </div>
                    <span className={`status-pill status-pill--${r.status === 'OPEN' ? 'published' : r.status === 'CLOSED' || r.status === 'RESOLVED' ? 'cancelled' : 'draft'}`}>
                      {r.status.replace(/_/g, ' ')}
                    </span>
                  </div>
                ))}
              </div>
            </>
          )}
        </>
      )}
    </div>
  );
}
