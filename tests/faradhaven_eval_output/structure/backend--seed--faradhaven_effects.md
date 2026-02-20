# Faradhaven_Effects

**Path:** `backend/seed/faradhaven_effects/`
**Purpose:** data seeding

## Overview

The `backend/seed/faradhaven_effects/` folder is responsible for seeding the `effects` table in the database with initial data related to various in-game effects for the Faradhaven campaign setting. It defines the structure of effect data and provides a function to populate the database using batch operations for efficiency. The folder ensures that the database is pre-populated with a consistent set of effects, using deterministic UUIDs to avoid duplication during reseeding. This is crucial for setting up a consistent game environment and providing a baseline for gameplay. The `seed.go` file uses the data defined in `effects.go` to create and upsert the effect records in the database.

## Files

### `effects.go`
**Role:** source file | **Lines:** 155

This file defines the `EffectSeed` struct, which represents the structure of an effect to be seeded into the database. It also contains the `AllEffects()` function, which returns a slice of `EffectSeed` structs, effectively providing the raw data for all the effects that need to be seeded. The `EffectSeed` struct includes fields like `Name`, `Description`, `Category`, and `Mechanics`. This file is essentially a data definition file, providing the content that will be used by `seed.go` to populate the database.

**Key Exports:**
- `AllEffects`
- `EffectSeed`

---

### `seed.go`
**Role:** source file | **Lines:** 36

This file contains the `SeedFaradhavenEffects` function, which is responsible for seeding the `effects` table in the database. It retrieves the effect data from `effects.go` using the `AllEffects()` function. It then iterates through the effect seeds, generates deterministic UUIDs for each effect using the `uuids` package, and creates `models.Effect` instances. Finally, it uses the `batch.UpsertBatchUpdateAll` function to efficiently insert or update the effect records in the database in batches, handling potential conflicts. This file orchestrates the data seeding process, ensuring that the database is populated with the initial set of effects.

**Key Exports:**
- `SeedFaradhavenEffects`

## Stats

- Total files: 2
- Has tests: no
- Has config: no
