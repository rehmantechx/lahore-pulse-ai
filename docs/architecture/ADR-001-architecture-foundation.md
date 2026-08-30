# ADR-001: Architecture Foundation

**Date:** 2026-08-14
**Status:** Accepted
**Deciders:** Lahore Pulse AI Engineering Team

## Context

Lahore Pulse AI is being built as a predictive city-intelligence platform for the Smart City Hackathon Lahore. The project starts from a blank repository and must establish a foundation that can grow into a production-grade system across multiple implementation phases.

The platform will eventually ingest environmental data from multiple open sources (OpenAQ, Open-Meteo, etc.), apply machine learning models, and produce risk assessments for air quality, heat, and flood scenarios in Lahore.

## Decision

We adopt a **layered architecture with explicit domain boundaries** for the following reasons:

### 1. Layered Architecture

```
API → Application → Domain → Infrastructure
```

**Rationale:**
- Separates HTTP concerns from business logic
- Allows the domain to be tested without HTTP overhead
- Makes it possible to add alternative interfaces (CLI, batch) later
- Prevents infrastructure changes from cascading into business logic

### 2. Domain-Driven Model Separation

We define distinct model types for:
- **Observations** (real measured data)
- **Forecasts** (external service predictions)
- **Predictions** (our ML model outputs)
- **Risk Assessments** (combined risk calculations)

**Rationale:**
- Prevents accidental conflation of observed vs. predicted data
- Makes data provenance explicit in the type system
- Enables different confidence/uncertainty profiles per data type
- Critical for explainability and audit requirements

### 3. Abstract Provider Contracts

External data sources are accessed through abstract interfaces (`DataProvider`, `ForecastProvider`).

**Rationale:**
- Source isolation: business logic never depends on specific HTTP clients
- Replaceability: sources can be swapped without changing consumers
- Testability: providers can be mocked via their interfaces
- Future-proofing: new sources implement the same contract

### 4. Explicit Provenance

Every observation carries full provenance metadata (source, timestamps, quality status).

**Rationale:**
- Environmental data quality varies significantly across sources
- The platform must be able to trace any output back to its inputs
- Trustworthiness of predictions depends on understanding input quality
- Hackathon judges will evaluate data handling rigor

### 5. Pydantic v2 for All Models

All domain models use Pydantic v2 with strong typing and validation.

**Rationale:**
- Runtime validation catches data errors at system boundaries
- Type annotations enable static analysis (mypy)
- Serialization/deserialization for API and storage
- Well-maintained, widely adopted in the Python ecosystem

### 6. Environment-Based Configuration

Configuration via `pydantic-settings` with environment variables (LPA_ prefix).

**Rationale:**
- Secrets never appear in source code
- Different environments (dev, test, prod) use the same config interface
- Type-safe configuration with validation at startup
- Follows twelve-factor app principles

### 7. Factory Pattern for FastAPI

Application created via `create_app()` factory function.

**Rationale:**
- Enables testing with different configurations
- Clear initialization order
- Supports dependency injection patterns

## Decisions Deliberately NOT Made

These are conscious postponements, not oversights:

| Decision | Rationale for Postponement |
|----------|---------------------------|
| No ML framework selected | No models to train in Phase 0; selection requires data exploration first |
| No database selected | No persistent state needed in Phase 0; schema-first approach preferred |
| No external API integration | Phase 0 is about contracts, not connections |
| No frontend architecture | Backend contracts must stabilize first |
| No prediction algorithm chosen | Requires historical data exploration and feature analysis |
| No authentication system | Not needed for Phase 0 API endpoints |
| No Docker/deployment config | Premature until the application has functional components |
| No caching layer | No performance bottlenecks to address yet |

## Consequences

### Positive
- Clean foundation for incremental growth
- Each phase can be implemented without restructuring
- Testable from day one
- Professional engineering practices established early

### Negative
- More initial code than a minimal prototype
- Some layers may seem "empty" until later phases add implementations
- Requires discipline to not bypass architectural boundaries

### Risks
- Over-engineering: mitigated by keeping Phase 0 scope strict
- Architecture drift: mitigated by this ADR and the development contract
- Premature abstraction: mitigated by only creating contracts that have clear use cases

## References

- [Development Guide](../development/DEVELOPMENT.md)
- [Project README](../../README.md)
