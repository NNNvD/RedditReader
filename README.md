# RedditReader

Personal, non-commercial, single-user utility for accessing and organizing posts and comments saved on my own Reddit account through Reddit's OAuth Data API.

## Status

**Pre-approval scaffold.** This repository exists to document the intended implementation for a Reddit Data API access request. The application is not operational until Reddit grants API access and OAuth client credentials are issued/configured.

## Intended use

RedditReader will authenticate the account owner through OAuth and retrieve that authenticated user's saved posts and comments for private review and personal knowledge management.

The application is intentionally narrow:
- single-user and non-commercial;
- accesses only the authenticated user's saved-content listing;
- uses low-volume, paginated requests;
- exports reference metadata by default rather than mirroring full post/comment bodies;
- preserves Reddit permalinks and provenance.

## API surface

Intended OAuth scopes:
- `identity` — verify the authenticated account;
- `history` — access the authenticated user's saved listing.

Intended endpoints:
- `GET https://oauth.reddit.com/api/v1/me`
- `GET https://oauth.reddit.com/user/{username}/saved`

## Non-goals

RedditReader will not:
- scrape Reddit at scale;
- access another user's private data;
- post, comment, vote, send messages, or moderate communities;
- resell Reddit data;
- use Reddit content to train an AI or machine-learning model.

## Data handling and security

OAuth credentials are supplied locally through environment variables and must never be committed to this repository. A refresh token, if issued, is stored only in a local ignored file. Exported saved-item metadata is also ignored by Git.

See [PRIVACY.md](PRIVACY.md) for the data-handling statement.

## Setup after Reddit approval

Requires Python 3.11+.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Then populate `.env` with the OAuth client information Reddit approves for the application. The redirect URI configured in Reddit must exactly match `REDDIT_REDIRECT_URI`.

## Usage

Authorize the account:

```bash
python reddit_saved_reader.py authorize
```

Retrieve up to 100 saved items and write reference metadata to a local JSON file:

```bash
python reddit_saved_reader.py list --limit 100 --output saved_items.json
```

The script derives the Reddit username from `/api/v1/me` rather than trusting a hard-coded username.

## Compliance

The implementation is designed for permitted OAuth access, an explicit User-Agent, conservative request volume, and local handling of the account owner's saved-content metadata. Actual use remains subject to Reddit's approval, Data API Terms, Developer Terms, rate limits, and any conditions Reddit attaches to the approved application.
