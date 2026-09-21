import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { api } from '../api/client';

export default function Help() {
  const [faqs, setFaqs] = useState([]);
  const [categories, setCategories] = useState([]);
  const [search, setSearch] = useState('');
  const [category, setCategory] = useState('');
  const [openId, setOpenId] = useState(null);
  const [info, setInfo] = useState({ supportEmail: '', supportPhone: '' });

  useEffect(() => {
    api.get('/comms/support-info/').then(setInfo).catch(() => {});
  }, []);

  useEffect(() => {
    const params = new URLSearchParams();
    if (search) params.set('search', search);
    if (category) params.set('category', category);
    api
      .get(`/comms/faqs/${params.toString() ? `?${params}` : ''}`)
      .then((data) => {
        setFaqs(data.faqs);
        setCategories(data.categories);
      })
      .catch(() => {});
  }, [search, category]);

  return (
    <div className="page">
      <section className="hero hero--slim">
        <h1>
          How can we <em>help?</em>
        </h1>
        <div className="hero__search">
          <input
            type="text"
            placeholder="Search FAQs — e.g. refunds, seats, tickets"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
      </section>

      {categories.length > 0 && (
        <div className="filter-row">
          <button className={`chip ${category === '' ? 'is-active' : ''}`} onClick={() => setCategory('')}>
            All topics
          </button>
          {categories.map((c) => (
            <button key={c} className={`chip ${category === c ? 'is-active' : ''}`} onClick={() => setCategory(c)}>
              {c}
            </button>
          ))}
        </div>
      )}

      {faqs.length === 0 ? (
        <div className="empty-state">
          <h3>No answers found.</h3>
          <p>Try different words — or open a support ticket below.</p>
        </div>
      ) : (
        <div className="faq-list">
          {faqs.map((f, i) => (
            <motion.div
              key={f.id}
              className={`faq ${openId === f.id ? 'is-open' : ''}`}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3, delay: Math.min(i * 0.03, 0.3) }}
            >
              <button className="faq__question" onClick={() => setOpenId(openId === f.id ? null : f.id)}>
                <span>{f.question}</span>
                <span className="faq__toggle">{openId === f.id ? '−' : '+'}</span>
              </button>
              {openId === f.id && <p className="faq__answer">{f.answer}</p>}
            </motion.div>
          ))}
        </div>
      )}

      <h2>Still stuck?</h2>
      <div className="help-cards">
        <Link to="/support" className="help-card">
          <h3>🎫 Support tickets</h3>
          <p>Open a ticket and track replies from our team.</p>
        </Link>
        <Link to="/support?tab=report" className="help-card">
          <h3>⚠ Report a problem</h3>
          <p>Flag an event, organiser, booking or technical issue.</p>
        </Link>
        <Link to="/messages" className="help-card">
          <h3>✉ Contact an organiser</h3>
          <p>Use the button on any event page to start a conversation.</p>
        </Link>
      </div>

      {(info.supportEmail || info.supportPhone) && (
        <p className="muted" style={{ marginTop: '1.5rem' }}>
          Prefer to reach us directly?
          {info.supportEmail && (
            <>
              {' '}Email <a href={`mailto:${info.supportEmail}`}>{info.supportEmail}</a>
            </>
          )}
          {info.supportPhone && (
            <>
              {' '}· Phone <a href={`tel:${info.supportPhone}`}>{info.supportPhone}</a>
            </>
          )}
        </p>
      )}
    </div>
  );
}
