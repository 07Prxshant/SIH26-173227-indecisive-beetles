# Development

## Ownership boundaries

- ML owns `/ml`.
- Backend owns `/backend`.
- Frontend owns `/frontend`.
- Infrastructure owns `/infra`.
- Shared contracts live under `/contracts`.

Do not edit another workstream's directory without coordination. Contract changes must be reviewed by affected producers and consumers and documented in the same commit.

## Local setup

1. Copy `.env.example` to `.env` and set an appropriate local database password.
2. Start the infrastructure skeleton with `docker compose -f infra/docker-compose.yml up` once Docker is available.
3. Each workstream will add its own package-level setup and test commands.

## Contract-first workflow

Before integrating services, validate event messages against `contracts/event.schema.json` and API responses against `contracts/incident.schema.json`. `contracts/api.yaml` is the source of truth for the REST surface.

## Contribution checks

Before every commit, run the tests, formatters, linters, and import/build checks available for the files you changed. Inspect `git diff` and do not commit `.env`, credentials, raw datasets, model weights, virtual environments, or `node_modules`.
