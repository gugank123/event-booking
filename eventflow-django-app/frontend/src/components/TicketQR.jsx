import { QRCodeSVG } from 'qrcode.react';

/** Scannable door ticket: encodes the ticket's signed QR token (opaque, single-use). */
export default function TicketQR({ value, label, size = 128 }) {
  return (
    <div className="qr-block">
      <QRCodeSVG value={value} size={size} level="M" />
      <p>{label || value}</p>
    </div>
  );
}
