const BASE_URL = '/api/v1';
const DEFAULT_TIMEOUT_MS = 15000;

let requestCount = 0;

function generateRequestId(): string {
  requestCount += 1;
  return `fe-${Date.now().toString(36)}-${requestCount.toString(36)}`;
}

export class ApiError extends Error {
  status: number;
  code: string;
  requestId: string;
  details: unknown;
  constructor(status: number, code: string, message: string, requestId: string, details?: unknown) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.requestId = requestId;
    this.details = details;
  }
}

export class NetworkError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'NetworkError';
  }
}

export class TimeoutError extends Error {
  constructor() {
    super('Request timed out');
    this.name = 'TimeoutError';
  }
}

async function request<T>(
  method: string,
  path: string,
  body?: unknown,
  signal?: AbortSignal,
): Promise<T> {
  const url = `${BASE_URL}${path}`;
  const rid = generateRequestId();
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), DEFAULT_TIMEOUT_MS);

  // Combine external signal with timeout
  const combinedSignal = signal
    ? combineSignals(signal, controller.signal)
    : controller.signal;

  try {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      'X-Request-ID': rid,
    };

    const resp = await fetch(url, {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined,
      signal: combinedSignal,
    });

    clearTimeout(timeoutId);

    const respRid = resp.headers.get('X-Request-ID') || rid;
    let data: unknown;

    try {
      data = await resp.json();
    } catch {
      if (resp.status === 204) {
        return undefined as T;
      }
      throw new ApiError(resp.status, 'parse_error', 'Invalid JSON response', respRid);
    }

    if (!resp.ok) {
      const errData = data as Record<string, unknown> | undefined;
      const error = errData?.error as Record<string, unknown> | undefined;
      throw new ApiError(
        resp.status,
        (error?.code as string) || 'unknown',
        (error?.message as string) || resp.statusText,
        respRid,
        error?.details,
      );
    }

    return data as T;
  } catch (err) {
    clearTimeout(timeoutId);
    if (err instanceof ApiError || err instanceof NetworkError || err instanceof TimeoutError) {
      throw err;
    }
    if (err instanceof DOMException && err.name === 'AbortError') {
      if (signal?.aborted) {
        throw new NetworkError('Request cancelled');
      }
      throw new TimeoutError();
    }
    if (err instanceof TypeError && err.message.includes('fetch')) {
      throw new NetworkError('Cannot connect to server');
    }
    throw new NetworkError(err instanceof Error ? err.message : 'Unknown error');
  }
}

function combineSignals(s1: AbortSignal, s2: AbortSignal): AbortSignal {
  const controller = new AbortController();
  const onAbort = () => controller.abort();
  s1.addEventListener('abort', onAbort);
  s2.addEventListener('abort', onAbort);
  return controller.signal;
}

export function apiGet<T>(path: string, signal?: AbortSignal): Promise<T> {
  return request<T>('GET', path, undefined, signal);
}

export function apiPost<TRequest, TResponse>(
  path: string,
  body: TRequest,
  signal?: AbortSignal,
): Promise<TResponse> {
  return request<TResponse>('POST', path, body, signal);
}
