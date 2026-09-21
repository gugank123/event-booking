import { GoogleLogin } from '@react-oauth/google';

export const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID || '';

/**
 * Google Sign-In button. Renders Google's own button (which handles the
 * account chooser / One Tap UI) and hands the resulting ID token up via
 * onCredential(idToken). If no Client ID is configured yet, shows a hint
 * instead of crashing.
 */
export default function GoogleSignInButton({ onCredential, text = 'continue_with' }) {
  if (!GOOGLE_CLIENT_ID) {
    return (
      <p className="muted google-setup-hint">
        Google sign-in will appear here once a Client ID is set. See <code>frontend/.env</code> (
        <code>VITE_GOOGLE_CLIENT_ID</code>).
      </p>
    );
  }
  return (
    <div className="google-btn">
      <GoogleLogin
        text={text}
        shape="pill"
        width="100%"
        onSuccess={(response) => onCredential(response.credential)}
        onError={() => onCredential(null, 'Google sign-in failed. Please try again.')}
      />
    </div>
  );
}
