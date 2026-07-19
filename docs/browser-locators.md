# Browser locators

Locator resolution order:

1. OneOpen stable attribute (`data-oneopen-id`)
2. Accessible role + name
3. Associated label
4. Placeholder
5. Visible text
6. Stable business attributes
7. Parent/child relationship
8. Partial ID suffix (`[id$="_txtUsername"]`)
9. Partial ID contains (`[id*="Submit"]`)
10. CSS
11. XPath

## Element fingerprints

Each browser target stores a fingerprint with role, accessible name, text, parent/nearby text, stable selectors, and historical selectors. Candidates are scored 0–100.

## Policies

| Policy | Behaviour |
|---|---|
| Strict | Fail unless the approved locator matches |
| Suggest | Fail and return replacement suggestions |
| Controlled healing | Allow only when confidence ≥ threshold (default **90**) |

Healed locators are recorded with previous/new locator, confidence, build, workflow version, screenshot, approval status, and timestamp. Low-confidence matches are never silently accepted.
