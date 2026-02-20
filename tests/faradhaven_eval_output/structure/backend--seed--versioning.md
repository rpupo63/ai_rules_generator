# Versioning

**Path:** `backend/seed/versioning/`
**Purpose:** data seeding

## Overview

The `backend/seed/versioning/` folder manages the versioning and execution of database seeds. It ensures that seeds are only run when their content has changed or when they haven't been run successfully before. The primary mechanism is to compute a hash of the seed data and compare it against a stored hash in the `seed_metadata` table. This prevents unnecessary seed executions and maintains data consistency. The `version.go` file contains the core logic for computing seed hashes, retrieving seed metadata, and determining whether a seed should be executed.

## Files

### `version.go`
**Role:** source file | **Lines:** 93

The `version.go` file provides functions for managing seed execution based on content hashing. It includes functions to `ComputeSeedHash`, which generates a SHA256 hash of seed data after JSON serialization, ensuring deterministic hashing. `GetSeedMetadata` retrieves seed metadata from the database based on the seed name, and `ShouldRunSeed` determines if a seed should be executed by comparing the current hash with the stored hash or checking the status of the previous run. `RecordSeedRun` updates the seed metadata in the database, recording the start time, end time, status, and hash of the seed data. These functions interact with the `models` package to access the `SeedMetadata` struct and with the `gorm` package to interact with the database.

**Key Exports:**
- `ComputeSeedHash`
- `GetSeedMetadata`
- `ShouldRunSeed`
- `RecordSeedRun`
- `ClearSeedMetadata`

## Stats

- Total files: 1
- Has tests: no
- Has config: no
