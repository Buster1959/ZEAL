# Internationalisation Roadmap

## Shipped in Block 9

The Home Assistant setup flow includes translation JSON files for:

- Danish (`da`)
- Dutch (`nl`)
- English (`en`)
- Finnish (`fi`)
- French (`fr`)
- German (`de`)
- Italian (`it`)
- Norwegian Bokmål (`nb`)
- Spanish (`es`)
- Swedish (`sv`)

An automated test requires every language to have the same complete key schema
as English and rejects missing or blank values.

## Remaining before a translated panel release

The ZEAL HTML panel currently uses embedded English interface text. A future
localisation block must extract those strings into per-language frontend
dictionaries, select the Home Assistant user's locale with an English fallback,
and use locale-aware date, time, number and temperature formatting. Until that
work is complete, only the standard Home Assistant setup flow is translated;
the Overview, Schedule, Overrides, Learning and Setup pages remain English.

Translations should be reviewed by native speakers before a release describes
the entire ZEAL panel as translated.
