# Faradhaven Go Project


## Project Context

**Project Description:**
Faradhaven Go Project

**Technology Stack:**
- Primary Language: Go
- Frameworks: None specified
- Monorepo: No


## Project File Structure

**(root)/** - project root
  - `CLASS_SEEDING_REFACTOR_REPORT.md` (documentation)
  - `CLAUDE.md` (documentation)
  - `CONFUSING_LOGIC_AND_UI_REPORT.md` (documentation)
  - `DEPRECATION_REPORT.md` (documentation)
  (1 other source files)

  **backend/** - Go application
    - `.env.example` (environment variable template)
    - `docker-compose.yml` (Docker Compose configuration)
    - `go.mod` (Go module configuration)
    - `init-db.sql` (SQL query/migration)
    - `main.go` (Go entry point)
    (6 other source files)

    **backend/api/** - HTTP API endpoints and handlers
      - `middleware.go` (middleware)
      - `routes.go` (route definitions)
      - `types.go` (type definitions)
      (27 other source files)

    **backend/cmd/** - Command-line application entry points

      **backend/cmd/seed/** - Database seeding and test data generation
        - `main.go` (Go entry point)

    **backend/config/** - Application configuration management
      (1 other source files)

      **backend/config/yml/** - configuration files
        - `http.yml` (configuration)
        - `token.yml` (configuration)

    **backend/database/** - Data Access Layer (DAL) and GORM repositories
      (23 other source files)

    **backend/docs/** - Project documentation and guides
      - `DESCRIPTION_TO_SEED_PLAN.md` (documentation)
      - `RACE_SEED_GUIDE.md` (documentation)

    **backend/errs/** - Centralized error handling definitions
      - `services_infra.go` (service implementation) [exports: NewDNSError; IsTCPTimeoutError; IsTLSHandshakeError; IsConnectionResetError; IsOutOfMemoryError]
      - `services_llm.go` (service implementation) [exports: NewRateLimitError; IsModelOverloadedError; IsContextLengthError; IsContentPolicyError; IsBillingQuotaError]
      - `services_security.go` (service implementation) [exports: NewServiceUnreachableError; IsServiceDiscoveryError; IsSQLInjectionError; IsRequestForgeryError; IsSecretsLeakedError]
      - `services_system.go` (service implementation) [exports: NewConfigError; IsEnvironmentVariableError; IsSchemaVersionMismatchError; IsClockSkewError; IsPartialFailureError]
      (3 other source files)

    **backend/internal/** - Internal application components and utilities

      **backend/internal/bootstrap/** - Application initialization and bootstrapping
        (1 other source files)

    **backend/models/** - GORM data models and database schemas
      - `models.go` (data model/schema)
      (42 other source files)

    **backend/seed/** - Database seeding and test data generation
      (5 other source files)

      **backend/seed/batch/** - project files
        (1 other source files)

      **backend/seed/faradhaven_classes/** - data seeding
        - `types.go` (type definitions)
        (9 other source files)

      **backend/seed/faradhaven_effects/** - data seeding
        (2 other source files)

      **backend/seed/faradhaven_items/** - data seeding
        - `types.go` (type definitions)
        (3 other source files)

      **backend/seed/faradhaven_races/** - data seeding
        - `types.go` (type definitions)
        (22 other source files)

      **backend/seed/uuids/** - project files
        (1 other source files)

      **backend/seed/versioning/** - data seeding
        (1 other source files)

    **backend/services/** - Core business logic services
      - `component_interpreter_service.go` (service implementation) [exports: NewComponentInterpreterService; Interpret; DamageInstance; SpellResult; ComponentInterpreterService]
      - `corpse_service.go` (service implementation) [exports: NewCorpseService; HarvestCorpse; ConsumeCorpse; GetCorpse; GetCorpses]
      - `effect_service.go` (service implementation) [exports: NewEffectService; RemoveEffect; ModifyStacks; TickDuration; BreakConcentration]
      - `harvesting_service.go` (service implementation) [exports: NewHarvestingService; ConfirmHarvest; HarvestingService; HarvestableAbility; HarvestableAbilitiesResponse]
      - `hp_service.go` (service implementation) [exports: UpdateHP; SetTempHP; UseHitDice; ShortRest; LongRest]
      - `level_down_service.go` (service implementation) [exports: LevelDown]
      - `level_history_service.go` (service implementation) [exports: GetLevelHistory; GetLevelUpPreview]
      - `level_up_service.go` (service implementation) [exports: NewLevelUpService; filterFeaturesByArchetype; findClassLevelWithFeatures; LevelUpService; LevelUpRequest]
      - ... +7 more notable files
      (1 other source files)

  **docs/** - Project documentation and guides
    - `LORE_DIFFERENCES.md` (documentation)

  **frontend/** - project files


## Detailed Structure

Per-folder documentation is available in `.ai-rules/structure/`:

- [`backend--api.md`](.ai-rules/structure/backend--api.md) - backend/api/ (HTTP API endpoints and handlers)
- [`backend--cmd--seed.md`](.ai-rules/structure/backend--cmd--seed.md) - backend/cmd/seed/ (Database seeding and test data generation)
- [`backend--cmd.md`](.ai-rules/structure/backend--cmd.md) - backend/cmd/ (Command-line application entry points)
- [`backend--config--yml.md`](.ai-rules/structure/backend--config--yml.md) - backend/config/yml/ (configuration files)
- [`backend--config.md`](.ai-rules/structure/backend--config.md) - backend/config/ (Application configuration management)
- [`backend--database.md`](.ai-rules/structure/backend--database.md) - backend/database/ (Data Access Layer (DAL) and GORM repositories)
- [`backend--docs.md`](.ai-rules/structure/backend--docs.md) - backend/docs/ (Project documentation and guides)
- [`backend--errs.md`](.ai-rules/structure/backend--errs.md) - backend/errs/ (Centralized error handling definitions)
- [`backend--internal--bootstrap.md`](.ai-rules/structure/backend--internal--bootstrap.md) - backend/internal/bootstrap/ (Application initialization and bootstrapping)
- [`backend--internal.md`](.ai-rules/structure/backend--internal.md) - backend/internal/ (Internal application components and utilities)
- [`backend--models.md`](.ai-rules/structure/backend--models.md) - backend/models/ (GORM data models and database schemas)
- [`backend--seed--batch.md`](.ai-rules/structure/backend--seed--batch.md) - backend/seed/batch/ (project files)
- [`backend--seed--faradhaven_classes.md`](.ai-rules/structure/backend--seed--faradhaven_classes.md) - backend/seed/faradhaven_classes/ (data seeding)
- [`backend--seed--faradhaven_effects.md`](.ai-rules/structure/backend--seed--faradhaven_effects.md) - backend/seed/faradhaven_effects/ (data seeding)
- [`backend--seed--faradhaven_items.md`](.ai-rules/structure/backend--seed--faradhaven_items.md) - backend/seed/faradhaven_items/ (data seeding)
- [`backend--seed--faradhaven_races.md`](.ai-rules/structure/backend--seed--faradhaven_races.md) - backend/seed/faradhaven_races/ (data seeding)
- [`backend--seed--uuids.md`](.ai-rules/structure/backend--seed--uuids.md) - backend/seed/uuids/ (project files)
- [`backend--seed--versioning.md`](.ai-rules/structure/backend--seed--versioning.md) - backend/seed/versioning/ (data seeding)
- [`backend--seed.md`](.ai-rules/structure/backend--seed.md) - backend/seed/ (Database seeding and test data generation)
- [`backend--services.md`](.ai-rules/structure/backend--services.md) - backend/services/ (Core business logic services)
- [`backend.md`](.ai-rules/structure/backend.md) - backend/ (Go application)
- [`docs.md`](.ai-rules/structure/docs.md) - docs/ (Project documentation and guides)
- [`root.md`](.ai-rules/structure/root.md) - (root)/ (project root)

---

```markdown
# Faradhaven Go Project - AI Coding Rules

This document outlines the coding standards, best practices, and common pitfalls for the Faradhaven Go project. These rules are designed to ensure code quality, maintainability, and consistency across the project.

## Project Context

The Faradhaven project is a [describe project]. It's a relatively small project, so simplicity and clarity are paramount.

## Technology Stack

*   **Language:** Go (version 1.21 or later)
*   **Frameworks:** None specified. Standard library only.
*   **Monorepo:** No.

## Coding Standards

### Error Handling

Following patterns from awesome-cursorrules/codequality.mdc, we prioritize explicit error handling.

#### ❌ WRONG: Ignoring Errors

```go
package main

import "fmt"

func divide(a, b int) int {
	return a / b // Potential panic if b is zero
}

func main() {
	result := divide(10, 0)
	fmt.Println(result)
}
```

#### ✅ CORRECT: Explicit Error Handling

```go
package main

import (
	"fmt"
	"errors"
)

func divide(a, b int) (int, error) {
	if b == 0 {
		return 0, errors.New("division by zero")
	}
	return a / b, nil
}

func main() {
	result, err := divide(10, 0)
	if err != nil {
		fmt.Println("Error:", err)
		return
	}
	fmt.Println("Result:", result)
}
```

**Rule:** ALWAYS check for errors after every function call that returns an error. NEVER ignore errors.

### Naming Conventions

Following patterns from awesome-cursorrules/clean-code.mdc, we use descriptive and consistent naming.

#### ❌ WRONG: Cryptic Names

```go
package main

func calc(a, b int) int {
	r := a + b
	return r
}
```

#### ✅ CORRECT: Descriptive Names

```go
package main

func calculateSum(firstNumber, secondNumber int) int {
	sum := firstNumber + secondNumber
	return sum
}
```

**Rules:**

*   Variables and functions MUST have names that clearly indicate their purpose.
*   Use camelCase for variable and function names.
*   Constants MUST be in ALL_CAPS with underscores separating words.

### Constants

Following patterns from awesome-cursorrules/clean-code.mdc, we use constants instead of magic numbers.

#### ❌ WRONG: Magic Numbers

```go
package main

import "fmt"

func calculateCircleArea(radius float64) float64 {
	return 3.14 * radius * radius
}

func main() {
	area := calculateCircleArea(5)
	fmt.Println("Area:", area)
}
```

#### ✅ CORRECT: Using Constants

```go
package main

import "fmt"

const PI = 3.14159

func calculateCircleArea(radius float64) float64 {
	return PI * radius * radius
}

func main() {
	area := calculateCircleArea(5)
	fmt.Println("Area:", area)
}
```

**Rule:** ALWAYS use constants for values that have a specific meaning or are used multiple times.

### Code Structure

#### ❌ WRONG: Long Functions

```go
package main

import "fmt"

func processData(data []int) {
	// 50+ lines of code doing various things
	// Reading data, validating, transforming, printing, etc.
	fmt.Println("Processing data...")
	for _, d := range data {
		fmt.Println(d)
	}
	// ... more code ...
}
```

#### ✅ CORRECT: Small, Focused Functions

```go
package main

import "fmt"

func readData(data []int) {
    fmt.Println("Reading data...")
}

func validateData(data []int) {
    fmt.Println("Validating data...")
}

func transformData(data []int) {
    fmt.Println("Transforming data...")
}

func printData(data []int) {
	fmt.Println("Printing data...")
	for _, d := range data {
		fmt.Println(d)
	}
}

func processData(data []int) {
	readData(data)
    validateData(data)
    transformData(data)
	printData(data)
}
```

**Rule:** Functions MUST be small and focused, performing a single, well-defined task. Aim for functions under 50 lines.

## Testing

*   Write unit tests for all functions.
*   Use the `testing` package.
*   Test edge cases and error conditions.

## Common Pitfalls

*   **Ignoring Errors:** As shown above, ALWAYS check for errors.
*   **Magic Numbers:** Use constants instead.
*   **Long Functions:** Break down complex logic into smaller, more manageable functions.
*   **Lack of Documentation:** Document all public functions and types.

## Commands

*   `go build`: Builds the project.
*   `go test`: Runs the tests.
*   `go fmt`: Formats the code.
*   `go vet`: Analyzes the code for potential errors.

## Additional Notes

*   Refer to the Go documentation for best practices: [https://go.dev/doc/](https://go.dev/doc/)
*   Follow the principles of clean code and SOLID design.
*   When in doubt, ask a senior developer for guidance.
```