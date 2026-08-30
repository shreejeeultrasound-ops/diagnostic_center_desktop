# Assumptions & Implementation Decisions

The build brief was thorough, so most decisions were directly specified.
This file lists the places where a judgment call was still required,
what was decided, why, and how easy it would be to change.

## Repository state (Phase 1 finding)

The workspace was completely empty at the start of this task — no existing
code, configuration, or business-rule artifacts of any kind (confirmed by
listing `/home/claude`, `/mnt/user-data/uploads`, and searching for any
`.git`/`requirements.txt`/`package.json` markers). This is therefore a
greenfield build strictly from the build brief itself, not a modification
of prior work. Nothing was assumed beyond what the brief states.

## 1. Doctor/investigation name snapshotting on each transaction

**Decision**: `patient_investigations` stores both the FK (`doctor_id`,
`investigation_type_id`) *and* a text snapshot (`doctor_name_snapshot`,
`investigation_name_snapshot`) taken at the moment of capture.

**Why**: The brief states historical transaction data must "remain
stable even if master data changes later" as a general principle (§1,
§18), and doctor/investigation names are editable (§5.1/§5.2). An
FK-only design would let a later rename silently change how an old
report/DC displays. This was not explicitly requested for *names*
(only explicitly required for the fee), so it is flagged here as a
judgment call, not a literal requirement.

**To change**: drop the two snapshot columns and read `doctor.name` /
`investigation_type.name` through the FK at render time instead — a
small, localized change in `transaction_repository.py`,
`data_capture_service.py`, and the two PDF generators.

## 2. New transactions require an *active* doctor/investigation; edits do not

**Decision**: `DataCaptureService.create_transaction` rejects an
inactive doctor or investigation type. `update_transaction` does not —
it allows correcting an existing entry even if its doctor/investigation
has since been deactivated.

**Why**: §5 says inactive masters "should not normally appear in new
transaction dropdowns" and the acceptance scenario (§31 step 8)
requires that "historical DC/report generation still works" after
deactivation — but says nothing about blocking *edits* to old records
for a retired doctor. Blocking edits would force staff to reactivate a
retired doctor just to fix a typo in an old record, which seemed like
the wrong trade-off.

## 3. "Print" opens the generated PDF in the OS default viewer

**Decision**: The Print buttons on the DC and Customer Report screens
generate the PDF to a temp file and open it via
`QDesktopServices.openUrl`, relying on the system's default PDF viewer
and its native Print dialog, rather than a separate `QPrinter`-based
native rendering pipeline.

**Why**: Build brief §20 explicitly says "shared business functionality
should have one authoritative implementation" — a second, hand-built
print renderer duplicating the ReportLab layout would violate that and
risks the two outputs drifting apart. Every target Windows machine has
a PDF viewer with print support, so this meets the "direct printing"
requirement (§24) without duplicating the rendering logic.

## 4. Mobile number validation is permissive, not strictly 10-digit Indian

**Decision**: any mobile field accepts 6–15 digits rather than
enforcing exactly 10 digits.

**Why**: §6 says "text with appropriate validation" without specifying
an exact format, and staff may legitimately enter landline numbers with
STD codes or a country code prefix. Rejecting anything but a bare
10-digit number risked blocking valid real-world entries with no
stated business justification for the stricter rule.

## 5. Age range validated as 0–130

**Decision**: `age` must be a whole number between 0 and 130 inclusive.

**Why**: no explicit range was given; 130 is a generous outer bound
that catches obvious data-entry mistakes (e.g. typing "420") without
risking rejection of any real patient.

## 6. No authentication/login system

**Decision**: not implemented.

**Why**: explicitly out of scope for V1 unless required (§23, §32 —
"complex role-based access control" is listed as out of scope, and §23
says not to invent an auth system unless required). The application
still avoids exposing data unnecessarily and never sends data
externally.

## 7. Single schema-version stamp instead of a full migration framework

**Decision**: a `schema_version` table is created and stamped with
`1` on first run, rather than adopting Alembic.

**Why**: build brief §16 says "use migrations/versioning if
appropriate" — for a single-tenant local SQLite app with three tables
and no schema history yet, a dedicated migration framework is
unnecessary complexity (explicitly discouraged by §5 of the brief's
engineering principles). The version stamp gives a documented, honest
upgrade hook for V2 without that overhead now.

## 8. PyInstaller "onedir" build wrapped by Inno Setup, not a single .exe

**Decision**: PyInstaller produces a folder
(`dist/DiagnosticCenter/DiagnosticCenter.exe` + supporting files), and
Inno Setup packages that folder into one `Setup.exe` for distribution.

**Why**: §26 explicitly allows either approach and says to "prefer the
installer while also documenting the resulting executable/application
artifacts" if an installer is more reliable — a onedir build starts
faster than a onefile build (no self-extraction step on every launch)
and is easier to diagnose if something goes wrong on a user's machine,
while the Inno Setup installer still gives the end user the single
`Setup.exe` experience the brief asks for.

## 9. "DC" scope

**Decision**: implemented exactly as literally described in §9 — a
doctor-wise statement of patient/fee rows for a date range, with no
commission or payment-split logic.

**Why**: §9 explicitly instructs not inventing commission/payment
rules that were not specified, and to preserve the literal meaning
given rather than guessing at a different one. No repository evidence
existed to suggest otherwise.

## 10. Web edition: added staff login accounts (not in the original brief)

**Decision**: the web edition requires a login (username + bcrypt-hashed
password) before any screen is reachable, with a first-run "create the
admin account" flow instead of any seeded default credentials. Every
account has equal access — no admin/staff permission tiers.

**Why**: the original brief explicitly said not to build authentication
"unless required" (§23) for the desktop app, because whoever is
physically at that one PC already has implicit access control. That
assumption breaks the moment the same app is reachable from anywhere on
the internet — without a login, patient names, addresses, and phone
numbers would be visible to anyone who has the URL. This is a case
where the *reason* behind the original instruction (no access
mechanism existed that needed replacing) stopped applying once the
deployment model changed, rather than a case for inventing complexity
the brief didn't ask for. Kept deliberately flat (no roles/permissions
tiers) to match the spirit of "no complex role-based access control."

## 11. Web edition: SQLite kept, with a persistent-disk requirement documented instead of migrating to Postgres

**Decision**: the web edition uses the same SQLite database as the
desktop edition (same file, same WAL settings), rather than switching
to a client-server database like PostgreSQL.

**Why**: a single small diagnostic center's data volume and concurrent
staff count don't need a database server, and switching would add
operational complexity (a separate managed database to provision,
back up, and pay for) without a clear benefit at this scale. The real
risk with SQLite in a hosted setting is ephemeral container storage,
not the database engine itself — so that's solved directly by requiring
a persistent volume/disk on whatever host runs it (documented
prominently in `docs/WEB_DEPLOYMENT.md`) rather than by changing
database engines. If the clinic later needs multiple locations writing
concurrently, Postgres is a reasonable upgrade path then.

## 12. Web edition: CSRF token added on top of SameSite=Lax cookies

**Decision**: every state-changing form includes a per-session CSRF
token, checked on submit, in addition to the session cookie already
being SameSite=Lax + HttpOnly + Secure (over HTTPS).

**Why**: SameSite=Lax alone blocks most cross-site POST forgery, but
patient data is sensitive enough over the public internet to warrant
defense in depth rather than relying on a single browser-behavior
protection. This was a judgment call toward extra caution rather than
a literal requirement, since the original brief's V1 security section
(§23) predates the web edition existing at all.

## 13. Web edition: no scheduled/automatic backups, no rate limiting on login

**Decision**: backups remain a manual action (Settings → Backup
Database, which downloads a file), and there is no login-attempt
throttling or account lockout.

**Why**: keeping V1 scope bounded, matching the original brief's
repeated instruction not to add unrequested complexity. Both are
reasonable near-term follow-ups once real usage patterns are known
(e.g., a scheduled backup job, or a hosting-platform-level rate limit /
Cloudflare in front of the app) — flagged here rather than silently
built or silently ignored.
