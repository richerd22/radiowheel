# The Radio Wheel - source

Generator and content for radiowheel.cold.fyi, an independent cited guide to Rockstar Games' music. The site at the repo root is generated; edit here, then rebuild.

- `content/parts/NN-slug.md` - lede plus 11 sections. Footnotes are `[^key]`; keys map to URLs in `content/frag/*-sources.tsv`.
- `content/frag/tracks-*.json` - every song on every GTA station: game, station, artist, title, year, added, removed, note, source.
- `content/frag/stations-*.json`, `talk.json`, `hosts.json`, `lore.json`, `removals.json`, `circoloco-releases.json`, `online.json`, `people.json`, `gta6.json` - the modules. `gta6.json` rows carry a status: official, reported, leak or rumour.
- `content/quiz.json`, `seo.json`, `gaps.json` - quiz, home-page FAQ and title, open questions.
- Build: `RW_REPORT=src/content RW_OUT=. STRICT=1 python3 src/build.py`, then `python3 src/og.py <sources> <songs>` for the share image. Set `RW_UPDATED=YYYY-MM-DD` to stamp an update.

Rules: every fact footnoted to a page someone opened; leaks labelled as leaks; no lyrics; quotes under 25 words; no em or en dashes; independent of Rockstar, Take-Two, CircoLoco and every artist. Corrections go in `content/corrections.json` (`date`, `section`, `what`).
