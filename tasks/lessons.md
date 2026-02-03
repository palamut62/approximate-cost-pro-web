# Lessons Learned

## 2026-02-03: Provider Fallback Logic
- **Problem:** Gemini was used as a fallback despite user explicitly forbidding it.
- **Solution:** Removed fallback logic entirely and forced strict model usage.
- **Rule:** If user bans a provider, remove all code paths that might activate it.
