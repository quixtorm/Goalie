# Voice samples (Goalie narration)

All four samples read the same text (the "home" scene plus a sentence with "MCC" and "so'm", to compare pronunciation):

> Meet Goalie, an AI financial agent inside your banking app. Your goals live as subcards under your main card.
> A cinema purchase is checked by its MCC code, and every amount is shown in so'm.

| File | Engine | Voice | Length |
|---|---|---|---|
| `speko_openai_echo.wav` | Speko → OpenAI `gpt-4o-mini-tts` (with a "calm, clear, neutral pace" instruction) | `echo` (calm male) | 13.4 s |
| `speko_deepgram_flux-miles.wav` | Speko → Deepgram `flux` | `flux-miles-en` (calm American male) | 14.6 s |
| `speko_deepgram_aura2-thalia.wav` | Speko → Deepgram `aura-2` | `aura-2-thalia-en` (clear American female) | 12.3 s |
| `edge_en-US-AndrewNeural.mp3` | edge-tts (free, no key) | `en-US-AndrewNeural` (warm, confident male) | 12.1 s |

Speko samples are WAV because that is the format Speko returned (24 kHz mono).

**Default: `speko/openai:gpt-4o-mini-tts/echo`.** It is the only one of the four that takes a speaking-style instruction,
so the pace can be asked to stay calm and neutral. A speech-to-text check of this sample gave back "Goalie" and "MCC" as written.
"so'm" was not transcribed, which is expected for an Uzbek word an English recognizer doesn't know. The narration
script itself never says "so'm". Deepgram Miles was the slowest read (14.6 s for the same text), which would push the
video past 95 s. Note: these are machine choices, not a listening test. Listen to the four files and switch if you prefer another.

**Switch voice:** change `"voice"` in `qa/narration.json` to one of the keys in `voice_options`, then regenerate
(see `qa/video/report.md` → "Regenerate with another voice").

edge-tts note: the free edge-tts service sometimes answers "No audio was received" for a valid request;
`qa/narrate.py` retries with backoff.
