# AI Services
## Kimi k2.5 Configuration
- **Model ID:** `moonshotai/kimi-k2.5` (Note: `moonshot/kimi-k2.5` is invalid)
- **Timeout:** Increased to 120s due to high latency.
- **Rules:** 
  - Gemini is strictly disabled.
  - JSON mode `response_format` is NOT used as it may cause hangs; prompt engineering is used instead.
