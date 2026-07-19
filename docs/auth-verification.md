# Auth verification nodes

OneOpen Flow supports email verification, OTP extraction, TOTP, and human-in-the-loop OTP entry for login and MFA workflows.

## Nodes

| Node | Purpose |
|---|---|
| **Wait for Email** | Poll IMAP for a matching message |
| **Extract OTP from Email** | Parse a one-time code from the email body |
| **Extract Verification Link** | Find verify/confirm URLs (prefers `href` + verify keywords) |
| **Open Verification Link** | Open the extracted URL in the browser agent |
| **Generate TOTP** | Produce a code from a shared secret (`pyotp`) |
| **Verify TOTP** | Validate a code against the shared secret |
| **Human OTP Input** | Pause the run until an operator submits a code |
| **Fill OTP Field** | Type the OTP into a browser input |

## Typical flows

### Email magic link

```text
Wait for Email → Extract Verification Link → Open Verification Link → Assert dashboard
```

### Email OTP

```text
Wait for Email → Extract OTP from Email → Fill OTP Field → Assert logged in
```

### Authenticator (TOTP)

```text
Generate TOTP → Fill OTP Field
```

Store the TOTP seed as a secret, e.g. `TOTP_SECRET`.

### Human-in-the-loop

```text
… → Human OTP Input → Fill OTP Field → …
```

When **Human OTP Input** runs, the workflow status becomes `approval_required`. On the run details page, enter the code and click **Submit & resume**.

API:

```http
POST /api/runs/{run_id}/provide-input
{ "otp": "123456" }
```

## IMAP configuration

Prefer secrets — never hardcode mailbox passwords in workflow JSON:

| Config | Secret recommendation |
|---|---|
| `imapHostSecret` | `IMAP_HOST` |
| `usernameSecret` | `IMAP_USERNAME` |
| `passwordSecret` | `IMAP_PASSWORD` |

Optional filters: `subjectContains`, `fromContains`, `toContains`, `folder`, `unreadOnly`, `timeoutSeconds`.

## Security notes

- OTP values are treated as secrets in audit logs (values are not written to audit details).
- Prefer `{{secret.*}}` for IMAP and TOTP seeds.
- Human-entered OTPs are stored on the node output for the resume path — restrict run access accordingly.
