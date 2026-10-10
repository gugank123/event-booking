import { QRCodeSVG } from 'qrcode.react';

/** Scannable door ticket: encodes the ticket's signed QR token (opaque, single-use). */
export default function TicketQR({ value, label, size = 160 }) {
  const caption = label || 'Entry ticket';
  return (
    <div className="qr-block" role="img" aria-label={`Ticket QR code: ${caption}`}>
      <QRCodeSVG value={value} size={size} level="M" aria-hidden="true" />
      <p>{caption}</p>
    </div>
  );
}
