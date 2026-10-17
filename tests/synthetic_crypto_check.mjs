import { randomBytes, createCipheriv, createDecipheriv, createHash } from 'node:crypto';
import assert from 'node:assert/strict';

// Synthetic in-memory test only. Never load real NCAAF data or write keys/backups.
const payload = Buffer.from('SYNTHETIC-NCAAF-RECOVERY-CHECK\n'.repeat(50));
const key = randomBytes(32), nonce = randomBytes(12);
const enc = createCipheriv('aes-256-gcm', key, nonce);
const ciphertext = Buffer.concat([enc.update(payload), enc.final()]);
const tag = enc.getAuthTag();
function decrypt(data, secret, iv, authTag) {
  const dec = createDecipheriv('aes-256-gcm', secret, iv);
  dec.setAuthTag(authTag);
  return Buffer.concat([dec.update(data), dec.final()]);
}
assert.deepEqual(decrypt(ciphertext, key, nonce, tag), payload);
const sha256 = x => createHash('sha256').update(x).digest('hex');
assert.equal(sha256(decrypt(ciphertext, key, nonce, tag)), sha256(payload));
for (const mutation of [
  () => { const x = Buffer.from(ciphertext); x[0] ^= 1; return [x,key,nonce,tag]; },
  () => [ciphertext, randomBytes(32), nonce, tag],
  () => { const x = Buffer.from(tag); x[0] ^= 1; return [ciphertext,key,nonce,x]; },
  () => { const x = Buffer.from(nonce); x[0] ^= 1; return [ciphertext,key,x,tag]; },
]) assert.throws(() => decrypt(...mutation()));
key.fill(0);
console.log('SYNTHETIC_AES_GCM_PASS: no files, external I/O, uploads or persistent secrets');
