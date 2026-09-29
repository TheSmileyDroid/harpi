export class ApiError extends Error {
  constructor({ code, message, status }) {
    super(message);
    this.name = "ApiError";
    this.code = code;
    this.status = status;
  }
}

/**
 * @typedef {object} ApiClientOptions
 * @property {(path: string, init?: any) => Promise<any>} [fetchImpl]
 * @property {(error: ApiError) => void} [onError]
 * @property {RequestCredentials} [credentials]
 */

/**
 * @typedef {object} RequestOptions
 * @property {string} [method]
 * @property {unknown} [body]
 * @property {boolean} [silent]
 */

/**
 * @param {ApiClientOptions} [options]
 */
export function createApiClient({
  fetchImpl = (path, init) => globalThis.fetch(path, init),
  onError,
  credentials = "same-origin",
} = {}) {
  /**
   * @param {string} path
   * @param {RequestOptions} [options]
   */
  async function request(path, { method = "GET", body, silent = false } = {}) {
    let response;
    try {
      response = await fetchImpl(path, {
        method,
        credentials,
        headers:
          body === undefined
            ? undefined
            : { "Content-Type": "application/json" },
        body: body === undefined ? undefined : JSON.stringify(body),
      });
    } catch {
      const error = new ApiError({
        code: "network_error",
        message: "Cannot reach the panel API",
        status: 0,
      });
      if (!silent) {
        onError?.(error);
      }
      throw error;
    }

    let payload = null;
    try {
      payload = await response.json();
    } catch {
      payload = null;
    }

    if (!response.ok) {
      const envelope = payload?.error ?? {
        code: "error",
        message: "Request failed",
      };
      const error = new ApiError({
        code: envelope.code,
        message: envelope.message,
        status: response.status,
      });
      if (!silent) {
        onError?.(error);
      }
      throw error;
    }

    return payload;
  }

  return {
    signIn(token) {
      return request("/api/session", { method: "POST", body: { token } });
    },
    checkSession() {
      return request("/api/session", { silent: true });
    },
    status() {
      return request("/api/status");
    },
  };
}
