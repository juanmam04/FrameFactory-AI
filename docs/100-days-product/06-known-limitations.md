# 06 — Known limitations

- Ideas without API key use offline mocks (still useful for UX testing)
- Clipboard helper uses `pyperclip` if installed; otherwise select+copy from `st.code`
- **Research (AI)** uses model knowledge — **not** live web search/crawling. Always verify facts before publish.
- No Flow automation
- No YouTube publish tracking (UI says **Completed** = rendered, not published)
- Subtitles still not burned in Documentary assemble
- Metadata/thumbnail still manual
- Equal image duration (voice length / N), not per-shot timing
- Approving script auto-runs Flow with LLM when keys present (can use Advanced offline)
