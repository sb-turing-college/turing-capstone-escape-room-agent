const STORAGE_KEY = "haunted_manor_client_id";

/**
 * Identifies this browser/device against the backend for save/load (Phase
 * 2c) - no login, just a UUID persisted in localStorage. Generated once on
 * first use.
 */
export function getClientId(): string {
  let id = localStorage.getItem(STORAGE_KEY);
  if (!id) {
    id = crypto.randomUUID();
    localStorage.setItem(STORAGE_KEY, id);
  }
  return id;
}
