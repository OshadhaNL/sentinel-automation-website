import test from 'node:test';
import assert from 'node:assert/strict';
import { createDemoTester, getDemoTesters, signInDemo } from './demoAuth.js';

const admin = { role: 'admin' };

test('only admins may create testers', async () => {
  const details = { name: 'Blocked Tester', email: 'blocked@example.com', password: 'demo-pass-123' };
  for (const actor of [null, { role: 'tester' }]) {
    await assert.rejects(createDemoTester(actor, details), /Only administrators/);
  }
  assert.equal(getDemoTesters().some((tester) => tester.email === details.email), false);
});

test('created testers can sign in and returned profiles contain no password material', async () => {
  const account = await createDemoTester(admin, { name: '  Demo Tester  ', email: ' Demo.Tester@EXAMPLE.com ', password: 'demo-pass-123' });
  assert.equal(account.name, 'Demo Tester');
  assert.equal(account.email, 'demo.tester@example.com');
  assert.equal(account.role, 'tester');
  assert.equal(account.initials, 'DT');
  for (const profile of [account, ...getDemoTesters(), await signInDemo('DEMO.TESTER@example.com', 'demo-pass-123')]) {
    for (const field of ['password', 'passwordHash', 'salt']) assert.equal(field in profile, false);
  }
  await assert.rejects(signInDemo(account.email, 'wrong-password'), /Incorrect email or password/);
  await assert.rejects(createDemoTester(admin, { name: 'Duplicate', email: 'DEMO.TESTER@example.com', password: 'other-pass-123' }), /already exists/);
});

test('invalid details and the reserved admin email are rejected', async () => {
  const valid = { name: 'Valid Tester', email: 'valid@example.com', password: 'demo-pass-123' };
  await assert.rejects(createDemoTester(admin, { ...valid, name: ' ' }), /name/);
  await assert.rejects(createDemoTester(admin, { ...valid, email: 'not-an-email' }), /valid email/);
  await assert.rejects(createDemoTester(admin, { ...valid, password: 'short' }), /8 characters/);
  await assert.rejects(createDemoTester(admin, { ...valid, email: ' ADMIN@NORTHLARK.COM ' }), /already exists/);
});

test('the existing demo admin account still signs in', async () => {
  assert.equal((await signInDemo('admin@northlark.com', 'password123')).role, 'admin');
  await assert.rejects(signInDemo('unknown@example.com', 'demo-pass-123'), /Incorrect email or password/);
});

test('the built-in tester signs in with the tester role and cannot be duplicated', async () => {
  const tester = await signInDemo(' TESTER@NORTHLARK.COM ', 'password123');
  assert.equal(tester.role, 'tester');
  assert.equal(tester.email, 'tester@northlark.com');
  assert.equal(tester.name, 'Northlark Tester');
  assert.equal(getDemoTesters().filter((account) => account.email === tester.email).length, 1);
  await assert.rejects(signInDemo(tester.email, 'wrong-password'), /Incorrect email or password/);
  await assert.rejects(createDemoTester(admin, { name: 'Duplicate Tester', email: ' TESTER@NORTHLARK.COM ', password: 'another-pass-123' }), /already exists/);
  await assert.rejects(createDemoTester(tester, { name: 'Unauthorized', email: 'unauthorized@example.com', password: 'demo-pass-123' }), /Only administrators/);
});
