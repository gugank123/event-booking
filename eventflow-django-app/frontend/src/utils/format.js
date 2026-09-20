export function formatDate(iso) {
  const d = new Date(iso);
  return d.toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric', year: 'numeric' });
}

export function formatTime(iso) {
  const d = new Date(iso);
  return d.toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' });
}

export function formatMoney(amount) {
  return new Intl.NumberFormat(undefined, { style: 'currency', currency: 'USD' }).format(Number(amount));
}

export function lowestPrice(ticketTypes) {
  if (!ticketTypes || ticketTypes.length === 0) return null;
  return Math.min(...ticketTypes.map((t) => Number(t.price)));
}

export function totalRemaining(ticketTypes) {
  if (!ticketTypes) return 0;
  return ticketTypes.reduce((sum, t) => sum + Math.max(0, t.quantity_total - t.quantity_sold), 0);
}
