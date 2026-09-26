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
2. Run PostgreSQL with PostGIS and Kafka or Redpanda locally, using the connection settings in `.env`.
3. Each workstream will add its own package-level setup and test commands.

## Contract-first workflow

Before integrating services, validate event messages against `contracts/event.schema.json` and API responses against `contracts/incident.schema.json`. `contracts/api.yaml` and `docs/api-contract.md` define the REST and WebSocket surface.

## Contribution checks

Before every commit, run the tests, formatters, linters, and import/build checks available for the files you changed. Inspect `git diff` and do not commit `.env`, credentials, raw datasets, model weights, virtual environments, or `node_modules`.
