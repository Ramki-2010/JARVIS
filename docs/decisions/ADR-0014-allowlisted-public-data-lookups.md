# ADR-0014 — Allowlisted, Read-Only Lookups of Public Data (weather, tech news, Indian news)

**STATUS: PROPOSED** (RK decided the scope in chat on 2026-11-13; this text becomes ACCEPTED only when RK merges the pull request that adds it, ADR-0001 D6)

| Field | Value |
|---|---|
| ID | ADR-0014 |
| Title | Allowlisted, read-only lookups of public data: weather, tech news and Indian news |
| Status | PROPOSED |
| Drafted | 2026-11-13, by Local Claude, from RK's chat decision |
| Authority class | USER AUTHORITY REQUIRED (G-05 for the firewall rule and the policy entry, G-13 for any install) |
| Inputs | ADR-0006 (no network in the control plane). ADR-0011 D2, D3 (process and server rules). ADR-0012 (voice has no network). ADR-0013 Amendment 1 (model output is untrusted text). Beta plan BR-9, BU-5, B-13, D-13. Master Context section 30 (network access belongs to Phase 3, as amended by MCA-001) |
| Amends | The Beta plan (section 13, Amendment 3, below). Nothing else |

**Labels:** `PROPOSED` · `USER AUTHORITY REQUIRED` · `UNKNOWN` · `RK ACT` · `MEASURED` · `UNVERIFIED`.

## 1. Context and the conflict, stated plainly

RK decided on 2026-11-13 that the Beta should let JARVIS look up **weather (Open-Meteo)**, **tech news (Hacker News)** and **all Indian news**, and nothing else. Google Keep and Google Tasks are out. RK also asked for time in other time zones, which needs no network (section 4).

This conflicts with text already in force: the control plane has no network (ADR-0006); the Master Context puts any network access behind Phase 3 Local Isolation; the Beta plan lists "no network or browsing" in the release notes (B-13) and requires the no-network static check to pass (BR-9); the voice runtime has no outbound connection (BU-5); and three JARVIS programs are blocked outbound by firewall rules (D-13). RK is the owner and may widen scope; ADR-0001 requires the widening to be recorded and bounded. This ADR is that record. It does not claim to be Phase 3 isolation. It is a much smaller control: a fixed list of lookups, in one separate component, with hard limits and an audit trail.

## 2. Decision (all items PROPOSED)

### D1. Scope: exactly these lookups
| Lookup | Source | Returned to the user |
|---|---|---|
| Weather now and today | Open-Meteo forecast API, and its geocoding API for a place name | temperature, conditions, wind, rain chance; numbers only |
| Tech news | Hacker News official API (`hacker-news.firebaseio.com`) | story title, score, the site's host name |
| Indian news | RSS feeds of five named publishers (list below) | headline, source, time; link on screen only |
| Time in other zones | none: offline (section 4) | the time |

Indian news feeds, all answering with RSS on 2026-11-13 (`MEASURED` by Local Claude from its own tool, not from JARVIS): The Hindu (national, business), Indian Express (India), NDTV (India, via Feedburner), Times of India (top stories), Hindustan Times (India). **RK confirms or changes this list; the list is part of this decision.** The publishers' own terms for feed use are `UNVERIFIED`; only headline, source, time and link are used, for RK's personal reading, nothing is republished.

Everything else stays unsupported. JARVIS still says plainly that it cannot do it and offers to note it.

### D2. One component, outside every existing package
- A new package `fetcher/` is the **only** code allowed to import `socket`, `ssl`, `http.client` or `urllib`. `jarvis/`, `advisor/`, `ui/` (apart from its localhost server), `voice/` and `interaction/` stay free of them. The static checks (ADR-0011 D2, ADR-0012) are extended to say so.
- It runs as a **short-lived child process**, `python -I -m fetcher <lookup> <arguments>`, started by one new named helper, `interaction/fetch_child.py`, which becomes the **third** process-creating site (after `interaction/child.py` and `interaction/voice_child.py`). Same form: absolute interpreter path, no shell, minimal environment, a timeout, bounded output. The static test names all three.
- The child returns JSON on standard output and exits. It holds no state, no cache across runs, no credentials.

### D3. Hard limits, fixed in code and tested
1. **Fixed hosts and fixed paths.** One adapter per lookup, with its host and path template written in the code. No generic "fetch this URL". The user cannot supply a URL. Hosts: `api.open-meteo.com`, `geocoding-api.open-meteo.com`, `hacker-news.firebaseio.com`, and the feed hosts of D1 (to be pinned exactly when RK confirms the list).
2. **HTTPS only, certificate checked, no redirects** (a redirect is an error), GET only, no cookies, no authentication, no request header beyond a generic `User-Agent: JARVIS-local`. No personal detail is ever sent.
3. **Bounded**: response at most 512 KB (the largest feed measured on 2026-11-13 was 216 KB), connect and read timeout 8 s, at most 6 lookups a minute. There is no cache in v1.
4. **Validated inputs.** A place name: letters, spaces, dot and hyphen, at most 40 characters. News: a category from a fixed list and an optional keyword (letters, digits, spaces, at most 30) used only to filter locally. Coordinates: numbers in range.
5. **Strict parsing.** JSON by `json.loads`. RSS only after rejecting any document type or entity declaration (blocks entity-expansion attacks), then the standard library parser, at most 30 items, tags stripped from titles. Anything that does not parse is "could not read that", with no partial guess.
6. **Reduced output.** Only the fields named in D1 leave the child. No article text, no description, no image, no script.

### D4. Fetched text is untrusted data
Everything returned is untrusted (ADR-0010 D5, ADR-0013). It is shown and spoken with control characters neutralised. It is **never** given to the model, never used as a command argument, never followed as an instruction. In the Beta the model does not summarise news: headlines are read as they are. Filtering by keyword or category is done by plain code.

### D5. Policy and audit
A new capability, `FETCH_PUBLIC_DATA`, scoped by lookup name, is evaluated by policy for each lookup. `RK ACT`: RK adds it to the policy file (a governance file). Each lookup is recorded in the audit chain: lookup name, host, result (ok, refused, failed), bytes, duration. The place name and keyword are not recorded. Two new control-plane commands do this (`fetch authorize <lookup>` before, `fetch record <lookup> ...` after); the control plane itself still opens no socket and starts no process (ADR-0006 stands).

### D6. Firewall (RK ACT, G-05)
The fetcher runs from its **own private copy of Python 3.14** (as the voice does with 3.10), so an outbound-allow rule can name that one executable and every other JARVIS program stays blocked. Windows' firewall cannot restrict by host name (`UNVERIFIED` whether Windows 11 FQDN rules are available here), and IP-level rules do not suit sites behind content networks. So the host list is enforced by the code (D3), by tests, and by the audit record, not by the firewall alone. Removing the rule switches all lookups off.

### D7. Failure behaviour
No internet, a blocked host, a timeout or a parse problem each produce one plain sentence from JARVIS ("I could not reach the weather service, sir"). Nothing else is affected and nothing is retried in a loop. `fetch_enabled = false` in the configuration (RK's file) disables the feature without removing the firewall rule.

### D8. Conversation
New deterministic intents only: weather (now, in a place), Hacker News tech news, Indian news (top, or a category, or a keyword). A reply is formed from the fixed fields by code. The persona text says the model itself still cannot look anything up; the system can fetch these three things for it.

## 3. What is deliberately not done
No browsing, no arbitrary URL, no search engine, no model with network, no Google account sign-in, no stored token or key, no unofficial Keep access, no email, no write to any remote service. Google Keep has no official API for personal accounts (Google's own announcement says Workspace enterprise only); Google Tasks needs an account sign-in and a stored token and is out by RK's decision.

## 4. Time in other zones (no network)
The control plane's Python has no time-zone database on this machine (`MEASURED` 2026-11-13: `ZoneInfoNotFoundError`). The pure-data package `tzdata` supplies it offline, with no compiled file for Smart App Control to block. Installing it is a G-13 item needing RK's per-item approval, and is independent of this ADR.

## 5. Beta plan effects (Amendment 3)
| Item | Change |
|---|---|
| B-13 release notes | "No network or browsing" becomes "no browsing; three named public lookups (weather, Hacker News, five Indian news feeds), read-only, audited" |
| BR-9 / X-13 | Unchanged for `jarvis/`, `advisor/`, `ui/`, `voice/`. `fetcher/` is the single named exception |
| BU-5 | Voice still has no outbound connection |
| New acceptance | BU-10: every limit in D3 has a test (wrong host, redirect, oversize, slow, malformed and hostile RSS, hostile headline text); the three process-creating sites are named by the static test; `FETCH_PUBLIC_DATA` denied means no lookup; firewall rule absent means a plain failure sentence |
| Cut order | The lookups are added scope. They are cut **first** if the date is at risk (before Stage B task create), not the conversation, galaxy or voice |
| Date | Not changed by this ADR. If the build threatens 29 Nov, the cut above is applied and reported the same day |

## 6. Consequences and unknowns
- **Gain:** weather and news by voice with a small, auditable, switch-off-able attack surface.
- **Cost:** a third process site, a private Python copy, a firewall rule, two control-plane commands, a policy entry, and the tests of D3. None is built until RK merges this ADR.
- **Risk:** a news publisher or Open-Meteo changes format or terms; the fetcher then fails with a plain sentence. Open-Meteo's free tier is for non-commercial use (`MEASURED` from its terms page, 2026-11-13: under 10,000 calls a day, credit required); this is personal use.
- **Privacy:** a weather lookup for a named place sends that place name (or coordinates) to Open-Meteo. RK sets a default place; nothing else about RK is sent.
- **`UNVERIFIED`:** that the Python standard library's compiled modules in a private 3.14 copy load under Smart App Control (the voice's 3.10 copy did; the 3.14 copy is untested); the feed publishers' terms; FQDN firewall rules.
- **`RK ACT` list:** confirm the feed list and a default place; add `FETCH_PUBLIC_DATA` to the policy; create the private Python copy's firewall rule; decide on `tzdata`.
