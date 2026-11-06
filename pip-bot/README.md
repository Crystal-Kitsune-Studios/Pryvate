# Pip 🦊

A consent-first, self-hostable prototype for Pryvate, a Crystal Kitsune Studios project. Pip searches for **possible** public listings and helps people find the official opt-out flow. This is a first working CLI, not the finished public service.

## What works

- Searches for a name on Spokeo and Whitepages using a self-hosted SearXNG instance and public search indexes.
- Displays up to ten possible results per broker with official opt-out links.
- Creates a deletion request draft for human review. It never sends emails or submits forms.
- Runs interactively and does not write names or results to files itself. Results are displayed in your terminal.

## What doesn't work yet

Pip does **not** directly scrape broker profiles, verify identity or ownership, automatically remove information, track requests, support multiple users, integrate with the Pryvate website, or run on a schedule. A lack of results is not evidence that the broker doesn't have a record. Indexes may be incomplete or outdated. You must verify every result manually. Some brokers require official forms, verification, or extra steps.

## Privacy and security

Search only for yourself or a person who has authorized you. Pip sends search terms by POST to the SearXNG service on **this machine** at `127.0.0.1:8888`; SearXNG then sends queries to whichever upstream engines it is configured to use. Those engines, your SearXNG installation, terminal scrollback, monitoring software, and browser history may retain data. No data stays private merely because Pip itself doesn't write a file. Do not enter SSNs, ID documents, phone numbers, or addresses here. Use only a name and an optional city/state. Verify opt-out destinations before sharing identifying information.

This is a single-user local CLI, **not safe for direct public internet exposure**. It has no accounts, access control, encryption at rest, or rate limits for a multi-user service. SearXNG is bound to localhost. For StarServer, run Pip in an SSH session on StarServer rather than exposing port 8888. A public Pryvate service will need a separate security design.

## Start on Linux with Docker Compose

Requires Python 3.10+, Docker, the Docker Compose plugin, and an internet connection. SearXNG is open-source; Docker and upstream search engines may have their own costs, policies, and availability. The image tag is unpinned in this prototype; pin and audit it for production. It may pull a sizable image.

From this folder, create a random Compose secret (the `.env` file is local and git-ignored). This refuses to overwrite an existing `.env`:

```sh
umask 077; (set -C; printf 'SEARXNG_SECRET=%s\n' "$(openssl rand -hex 32)" > .env)
```

```sh
docker compose up -d
```

```sh
python3 pipbot.py brokers
```

```sh
python3 pipbot.py scan
```

Search only one broker if preferred:

```sh
python3 pipbot.py scan --broker spokeo
```

Draft a request for review:

```sh
python3 pipbot.py draft --broker whitepages
```

Stop the service:

```sh
docker compose down
```

If search responds with HTTP 403, verify that the mounted SearXNG settings enable the `json` format, then restart the container. Search engine availability and blocking vary. A failed query is shown as a failure, not as proof of no listing. Don't bypass CAPTCHAs or access controls. Review the configured search engines and their terms before using this in a public service.

## Tests

```sh
python3 -m unittest discover -s tests -v
```

Tests are offline and use a fake search service. They do not prove a live SearXNG deployment or external search engines work. No real names are used.

## Sources

- SearXNG Search API: https://docs.searxng.org/dev/search_api.html
- Spokeo opt-out: https://www.spokeo.com/optout
- Whitepages consumer rights: https://www.whitepages.com/privacy/consumer-rights

## License

MIT. This prototype is not legal advice.
