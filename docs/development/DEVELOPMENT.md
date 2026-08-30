# Development Guide

This document defines the engineering rules and principles that all implementation phases must follow.

---

## Data Integrity

**Never fabricate missing values.**

- If data is unavailable, represent it as unavailable
- If a sensor reading doesn't exist, don't invent one
- If a prediction cannot be made, return insufficient confidence
- Synthetic data must never appear as real data

## Source Isolation

**External APIs must be accessed through replaceable provider interfaces.**

- Business logic depends on abstract contracts, not HTTP clients
- Each data source has its own provider implementation
- Providers can be swapped without changing consumers
- Tests mock the provider interface, not HTTP responses

## Domain Isolation

**Business logic must not depend directly on infrastructure.**

- Domain models have no imports from `infrastructure/`
- Domain models have no imports from `api/`
- The application layer orchestrates, the domain layer defines

## Explainability

**Every prediction and risk output must have an understandable chain.**

```
Input Data → Feature Preparation → Model → Prediction → Risk Assessment
     ↓              ↓                  ↓           ↓              ↓
  Provenance    Engineering      Model ID    Confidence    Contributing
  & Quality     Decisions        & Version   & Interval    Factors
```

## Reproducibility

**A model result must be traceable to its model version and input data.**

- Every `Prediction` carries `model_id` and `model_version`
- Every `Observation` carries full provenance
- Future: training runs will be logged with data snapshots

## Graceful Degradation

**One unavailable provider must not destroy unrelated functionality.**

- Data providers fail independently
- Missing air quality data should not prevent weather display
- Each provider has its own health check and error handling
- The readiness endpoint reports each component's actual state

## Explicit Uncertainty

**Insufficient data must produce insufficient confidence, not false certainty.**

- Every confidence-bearing model carries a `Confidence` object
- Confidence levels range from 0.0 (no confidence) to 1.0 (certain)
- When data is insufficient, confidence must reflect that
- Never present a guess as a certain prediction

## Incremental Implementation

**Future phases must modify the architecture deliberately, not bypass it.**

- New data sources implement existing provider contracts
- New domain concepts get their own models in `domain/models/`
- New API endpoints follow the versioned router pattern
- New infrastructure goes in `infrastructure/`, not in domain code

## Code Quality Standards

### Formatting & Linting
- **ruff**: linting and import sorting
- **ruff format**: code formatting (replaces black)
- **mypy**: static type checking

### Testing
- **pytest**: test runner
- Minimum test categories per phase:
  - Application startup
  - API endpoint behavior
  - Schema validation
  - Configuration validation
  - Domain contract tests

### Type Safety
- All function signatures should have type annotations
- Use `pydantic` for data validation at boundaries
- Use `enum` for fixed sets of values

## Development Workflow

### 1. Environment Setup
```bash
cd backend
pip install -r requirements.txt
pip install ruff mypy pytest pytest-cov pytest-mock hypothesis
```

### 2. Running the Server
```bash
uvicorn app.main:app --reload
```

### 3. Running Tests
```bash
pytest                    # All tests
pytest -m unit            # Unit tests only
pytest --cov=app          # With coverage
```

### 4. Code Quality Checks
```bash
ruff check app/ tests/    # Linting
ruff format app/ tests/   # Formatting
mypy app/                 # Type checking
```

### 5. Before Committing
- All tests pass
- No lint errors
- No type errors
- Documentation updated if architecture changed

## File Organization Rules

| Location | What belongs here |
|----------|------------------|
| `app/api/` | HTTP endpoints, request/response handling |
| `app/api/v1/` | Version 1 API endpoints |
| `app/core/` | Cross-cutting: config, logging, errors |
| `app/domain/models/` | Business data models |
| `app/domain/contracts/` | Abstract interfaces |
| `app/application/` | Use-case orchestration |
| `app/infrastructure/` | External integrations |
| `tests/` | Test files mirror `app/` structure |

## What NOT to Do

- Do not add API keys or secrets to source code
- Do not create fake data to make the system "appear" functional
- Do not implement features outside the current phase scope
- Do not bypass architectural boundaries for convenience
- Do not add dependencies without documenting why
- Do not claim functionality exists when it doesn't
