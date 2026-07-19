# ASPX support

ASP.NET Web Forms often generates unstable IDs such as `ctl00_ContentPlaceHolder1_txtUsername`.

## Recommendations

- Prefer `data-oneopen-id` with `ClientIDMode="Static"` when possible
- Use role/label/placeholder locators before IDs
- Use partial suffix matches for unavoidable WebForms IDs: `input[id$="_txtUsername"]`

## Engine behaviour

- Detect full postbacks and `__doPostBack`
- Handle `__VIEWSTATE` / `__EVENTVALIDATION` pages
- Wait for UpdatePanel completion
- Re-resolve locators after DOM replacement (no stale handles)
- Detect ASP.NET validation messages

Wait mode: **Wait for ASPX Postback Completion**
