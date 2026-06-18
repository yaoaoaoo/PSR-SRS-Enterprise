/** Pure client-side ID generation using crypto.randomUUID().

All functions are pure with respect to React rendering — they do not
call impure functions like Date.now() or Math.random().
*/

export function createClientId(prefix: string): string {
  return `${prefix}_${globalThis.crypto.randomUUID()}`;
}

export function createRequestId(): string {
  return createClientId("req");
}

export function createSessionId(): string {
  return createClientId("sess");
}

export function createEventId(action: string, requestId: string, itemId: string): string {
  return `${action}_${requestId}_${itemId}_${globalThis.crypto.randomUUID()}`;
}
