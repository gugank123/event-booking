import { QRCodeSVG } from 'qrcode.react';

/** Scannable door ticket: encodes the booking reference. */
export default function TicketQR({ reference, size = 128 }) {
  return (
    <div className="qr-block">
      <QRCodeSVG value={reference} size={size} level="M" />
      <p>{reference}</p>
    </div>
  );
}
