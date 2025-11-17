# Services

This directory contains the microservices that make up the VulnZero platform.

## Structure

- **aggregator/**: Vulnerability data ingestion and normalization
- **patch-generator/**: AI-powered patch generation using LLMs
- **testing-engine/**: Digital twin environment for patch testing
- **deployment-engine/**: Automated deployment and orchestration
- **monitoring/**: Post-deployment monitoring and rollback
- **api-gateway/**: Main API gateway (FastAPI application)

## Development

Each service is designed to be independently deployable. For MVP, we'll start with a monolithic approach where all services run in the same process, then split into microservices as needed.

## Getting Started

See the main [README.md](../README.md) for setup instructions.
