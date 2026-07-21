# NewsIntentRec Product Walkthrough

The React product presents a compact English news feed rather than a generic community
clone.

- Cards show a real MIND headline and abstract.
- Category/subcategory chips explain content grouping.
- `Source: <domain>` is explicitly a URL hostname, not a publisher attribution claim.
- Sponsored cards remain visibly labeled.
- Personas are named from dominant category preferences and do not expose raw user-ID
  meaning.
- Feed reasons identify profile category, recent query category, ALS, or fallback
  contribution.
- Search accepts category aliases and real headline/abstract terms. No-result input
  returns an explicit error.
- Search and click events update the local profile; the next feed debug payload can
  show `recent_query_topic`.

The demo is deliberately small and deterministic. It demonstrates interaction and
system behavior; full-data recommendation conclusions come from normalized MIND-small,
not from the three demo personas.
