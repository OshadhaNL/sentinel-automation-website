// Frontend demo only: this is a public preview credential, not secure authentication.
// Replace this adapter with the FastAPI login endpoint before real deployment.
// Created tester password hashes live in memory only; reloading clears created accounts.
const testers = new Map();
const adminEmail = 'admin@northlark.com';
const defaultTester = Object.freeze({
  id: 'demo-tester', name: 'Northlark Tester', email: 'tester@northlark.com',
  role: 'tester', initials: 'NT', isActive: true, createdAt: new Date().toISOString(),
});

function publicTester({ passwordHash, salt, ...tester }) {
  return tester;
}

async function hashPassword(password, salt) {
  const key = await crypto.subtle.importKey('raw', new TextEncoder().encode(password), 'PBKDF2', false, ['deriveBits']);
  const hash = await crypto.subtle.deriveBits({ name: 'PBKDF2', salt, iterations: 100000, hash: 'SHA-256' }, key, 256);
  return Array.from(new Uint8Array(hash), (byte) => byte.toString(16).padStart(2, '0')).join('');
}

export function getDemoTesters() {
  return [{ ...defaultTester }, ...Array.from(testers.values(), publicTester)];
}

export async function createDemoTester(actor, { name, email, password }) {
  if (actor?.role !== 'admin') throw new Error('Only administrators can create tester accounts.');
  const normalizedEmail = email.trim().toLowerCase();
  const normalizedName = name.trim();
  if (normalizedName.length < 2) throw new Error('Enter a name with at least 2 characters.');
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(normalizedEmail)) throw new Error('Enter a valid email address.');
  if (password.length < 8) throw new Error('Use a password with at least 8 characters.');
  if (normalizedEmail === adminEmail || normalizedEmail === defaultTester.email || testers.has(normalizedEmail)) throw new Error('An account with this email already exists.');
  const salt = crypto.getRandomValues(new Uint8Array(16));
  const passwordHash = await hashPassword(password, salt);
  // Check again after hashing, in case another form submitted the same email.
  if (testers.has(normalizedEmail)) throw new Error('An account with this email already exists.');
  const tester = {
    id: crypto.randomUUID(), name: normalizedName, email: normalizedEmail,
    role: 'tester', initials: normalizedName.split(/\s+/).slice(0, 2).map((part) => part[0]).join('').toUpperCase(),
    createdAt: new Date().toISOString(), isActive: true, passwordHash, salt,
  };
  testers.set(normalizedEmail, tester);
  return publicTester(tester);
}

export async function signInDemo(email, password) {
  if (email.trim().toLowerCase() === 'admin@northlark.com' && password === 'password123') {
    return { name: 'Northlark Admin', email: 'admin@northlark.com', role: 'admin', initials: 'NA' };
  }
  if (email.trim().toLowerCase() === defaultTester.email && password === 'password123') {
    return { ...defaultTester };
  }
  const tester = testers.get(email.trim().toLowerCase());
  if (tester?.isActive && await hashPassword(password, tester.salt) === tester.passwordHash) {
    return publicTester(tester);
  }
  throw new Error('Incorrect email or password. Please try again.');
}

export function createTesterPreview() {
  return { name: 'Sample Tester', email: null, role: 'tester', initials: 'TA' };
}
