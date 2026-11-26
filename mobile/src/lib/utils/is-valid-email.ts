// ABOUTME: A light shape check for an email address before it is sent anywhere; the auth
// ABOUTME: service remains the judge of whether the address is real.

export function isValidEmail(email: string): boolean {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}
