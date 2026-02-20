# Seed

**Path:** `backend/seed/`
**Purpose:** Database seeding and test data generation

## Overview

The `backend/seed/` folder is responsible for populating the database with initial data, including game-related entities like races, classes, items, and effects. It also handles database migrations related to UUIDs and data structure changes. The files within this folder work together to ensure a consistent and reproducible database state. `registry.go` defines the order in which seeds are executed, while `seeder.go` provides the framework for running these seeds and clearing data. The other files handle specific data migrations and initializations. This folder is crucial for setting up the application's initial state and providing a foundation for development and testing.

## Subfolders

- **`batch/`** - project files (1 files)
- **`faradhaven_classes/`** - data seeding (10 files)
- **`faradhaven_effects/`** - data seeding (2 files)
- **`faradhaven_items/`** - data seeding (4 files)
- **`faradhaven_races/`** - data seeding (23 files)
- **`uuids/`** - project files (1 files)
- **`versioning/`** - data seeding (1 files)

## Files

### `initialize_character_resources.go`
**Role:** source file | **Lines:** 123

This file focuses on initializing and backfilling character resources in the database. The `InitializeCharacterResources` function ensures that existing characters have a default amount of money. The `BackfillCharacterResources` function populates the `CharacterResource` table based on legacy character data. These functions are essential for migrating existing characters to a new resource management system or ensuring new characters have a baseline configuration. It interacts with the `models` package to access and update character data using the provided `gorm.DB` instance.

**Key Exports:**
- `InitializeCharacterResources`
- `BackfillCharacterResources`

---

### `migrate_uuids.go`
**Role:** source file | **Lines:** 495

This file contains the `MigrateToStableUUIDs` function, which performs a one-time migration to replace random UUIDs with deterministic UUIDs for various game entities. This migration is crucial for ensuring data consistency across different environments and reseeding operations. The function updates foreign key references to maintain data integrity. It calls helper functions like `migrateComponentUUIDs`, `migrateRaceUUIDs`, etc. to handle the migration for specific models. It uses the `uuids` subpackage to generate the deterministic UUIDs and interacts with the `models` package to update the database.

**Key Exports:**
- `MigrateToStableUUIDs`
- `migrateRaceUUIDs`
- `dropFKsReferencing`
- `migrateClassUUIDs`
- `migrateArchetypeUUIDs`
- `migrateComponentUUIDs`
- `migrateWeaponUUIDs`
- `NeedsUUIDMigration`
- `isExpectedUUID`

---

### `migrate_weapons_v2.go`
**Role:** source file | **Lines:** 55

This file contains the `MigrateCharacterWeaponsV2` function, which migrates character weapon data from a legacy many-to-many table (`character_weapons`) to a new explicit join table (`character_weapons_v2`). This migration is necessary to improve data modeling and allow for additional attributes on the join table. The function first checks if the legacy table exists and then inserts data into the new table, avoiding duplicates. It uses a transaction to ensure data consistency and interacts with the `models` package to define the structure of the new join table.

**Key Exports:**
- `MigrateCharacterWeaponsV2`

---

### `registry.go`
**Role:** source file | **Lines:** 58

This file defines the `AllSeeds` function, which returns a list of `Seed` structs that represent all registered database seeding operations. Each `Seed` struct contains the name of the seed, the function to execute the seed (`Run`), and a function to hash the seed data (`HashData`) for version checking. The order of the seeds in the returned slice is significant, as it determines the order in which they are executed. This file acts as a central registry for all seeding operations, coordinating the execution of seeds from different subfolders like `faradhaven_classes`, `faradhaven_effects`, `faradhaven_items`, and `faradhaven_races`.

**Key Exports:**
- `AllSeeds`

---

### `seeder.go`
**Role:** source file | **Lines:** 189

This file defines the `Seeder` struct and its associated methods for managing and executing database seeding operations. The `Seeder` struct holds a database connection (`gorm.DB`) and a list of `Seed` structs. It provides methods for registering seeds (`Register`, `RegisterAll`), clearing data (`ClearAllData`), and running the seeds. The `ClearAllData` function deletes data from specific tables to allow for fresh reseeding. The `Seed` struct defines the structure for individual seed operations, including the `Run` function that performs the actual seeding and the `HashData` function for version control. It interacts with the `models` package to clear data and with the `versioning` package to track seed versions.

**Key Exports:**
- `NewSeeder`
- `RegisterAll`
- `ClearAllData`
- `ClearAndSeed`
- `RunAll`
- `runSeeds`
- `HasData`
- `Seed`
- `Seeder`

## Stats

- Total files: 5
- Direct subfolders: 7
- Has tests: no
- Has config: no
