import { uploadResumeFile } from "./api";
import { hashFile, getCachedResume, cacheResume, type CacheEntry } from "./resumeCache";

export type UploadResult = {
  resumeId:   string;
  resumeData: Record<string, unknown>;
  entry:      CacheEntry;
  fromCache:  boolean;
};

export async function uploadResume(file: File): Promise<UploadResult> {
    console.log("1️⃣ uploadResume called:", file.name, file.size);
  // Step 1 — hash file bytes
  const hash = await hashFile(file);
    console.log("2️⃣ File hashed:", hash);
  // Step 2 — cache hit → return immediately, no API call
  const cached = getCachedResume(hash);
  if (cached) {
    console.log("✅ Cache hit:", cached.fileName, "·", cached.cachedAt);
    return {
      resumeId:   cached.resumeId,
      resumeData: cached.resumeData,
      entry:      cached,
      fromCache:  true,
    };
  }

  // Step 3 — cache miss → delegate fetch to api.ts
  console.log("📤 Cache miss — uploading:", file.name);
  const result = await uploadResumeFile(file);
  console.log("5️⃣ API response:", result);

  const resumeId = String(
    result.resumeId   ??
    hash
  );
  const resumeData =
    result.resumeData ??
    result;

  // Step 4 — store result in cache
  const entry: CacheEntry = {
    resumeId,
    resumeData,
    fileName: file.name,
    fileSize: file.size,
    cachedAt: new Date().toISOString(),
  };
  cacheResume(hash, entry);

  return { resumeId, resumeData, entry, fromCache: false };
}