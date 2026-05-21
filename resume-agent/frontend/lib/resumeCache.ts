    const CACHE_KEY = "resume_cache";
const MAX_CACHE_ENTRIES = 5;

// ─── Types ────────────────────────────────────────────────────────────────────

export type CacheEntry = {
  resumeId:   string;
  resumeData: Record<string, unknown>;
  fileName:   string;
  fileSize:   number;
  cachedAt:   string;
};

export type ResumeCache = Record<string, CacheEntry>;

// ─── localStorage ─────────────────────────────────────────────────────────────

export function readCache(): ResumeCache {
  try {
    return JSON.parse(localStorage.getItem(CACHE_KEY) || "{}");
  } catch {
    return {};
  }
}

export function writeCache(hash: string, entry: CacheEntry): void {
  try {
    const cache = readCache();
    cache[hash] = entry;
    const keys = Object.keys(cache);
    if (keys.length > MAX_CACHE_ENTRIES) {
      const oldest = keys.sort(
        (a, b) =>
          new Date(cache[a].cachedAt).getTime() -
          new Date(cache[b].cachedAt).getTime()
      )[0];
      delete cache[oldest];
    }
    localStorage.setItem(CACHE_KEY, JSON.stringify(cache));
  } catch {
    console.warn("Could not write to localStorage cache");
  }
}

export function clearCache(): void {
  localStorage.removeItem(CACHE_KEY);
}

export function getCacheCount(): number {
  return Object.keys(readCache()).length;
}

export function getCachedResume(hash: string): CacheEntry | null {
  return readCache()[hash] ?? null;
}

export function cacheResume(hash: string, entry: CacheEntry): void {
  writeCache(hash, entry);
}

// ─── File Hashing ─────────────────────────────────────────────────────────────

export async function hashFile(file: File): Promise<string> {
  const buffer = await file.arrayBuffer();
  const hashBuffer = await crypto.subtle.digest("SHA-256", buffer);
  return Array.from(new Uint8Array(hashBuffer))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}