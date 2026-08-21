# Privacy and data handling

RedditReader is intended as a private, single-user utility for the account owner.

## Data accessed

The application is designed to access only:
- the authenticated Reddit account identity;
- the authenticated user's saved posts and comments;
- metadata needed to identify and revisit those saved items, such as Reddit thing ID, type, subreddit, title or comment context, author where returned by the API, permalink, and creation timestamp.

## Local storage

OAuth secrets and tokens are stored locally and are excluded from Git. Exported saved-item data is also intended to remain local and is excluded from version control.

## Data minimization

The default export is intended to retain reference metadata rather than create a wholesale mirror of Reddit content. Full post or comment bodies are not required for the initial use case.

## Sharing and commercialization

The application is not intended to sell, license, publish, or redistribute Reddit user data. It is not intended for advertising, profiling, surveillance, or model training.

## Deletion

Local exports and OAuth tokens can be deleted by the account owner at any time. Revoking the Reddit application's authorization terminates future authenticated access.

## Compliance boundary

This repository documents intended behavior. Actual operation is contingent on Reddit granting Data API access and remains subject to Reddit's applicable terms, policies, rate limits, and approval conditions.
