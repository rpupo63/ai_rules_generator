# Uuids

**Path:** `backend/seed/uuids/`
**Purpose:** project files

## Overview

The `backend/seed/uuids/` folder is crucial for generating consistent and predictable UUIDs (Universally Unique Identifiers) for various game entities during the seeding process. It leverages the `github.com/google/uuid` library to create UUIDs based on predefined namespaces and entity names. This ensures that the same entity name always results in the same UUID, which is essential for data consistency and referential integrity across the application. The folder contains a single file, `uuids.go`, which defines the namespaces and functions for generating these deterministic UUIDs. These UUIDs are used to uniquely identify races, classes, components, and other game-related data.

## Files

### `uuids.go`
**Role:** source file | **Lines:** 131

This file defines a set of namespace UUIDs and functions to generate deterministic UUIDs for game entities. It imports the `github.com/google/uuid` library for UUID generation. The file declares several `Namespace...` variables, each a fixed UUID serving as a namespace for a specific entity type (e.g., Race, Class, Component). It also provides functions like `RaceUUID`, `ClassUUID`, `ComponentUUID`, etc., which take an entity name (and sometimes related entity names) as input and generate a UUID v5 (SHA1) based on the corresponding namespace. These functions are used during the database seeding process to ensure consistent UUIDs for entities with the same names.

## Stats

- Total files: 1
- Has tests: no
- Has config: no
