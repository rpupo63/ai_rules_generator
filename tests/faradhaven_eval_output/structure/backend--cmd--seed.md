# Seed

**Path:** `backend/cmd/seed/`
**Purpose:** Database seeding and test data generation

## Overview

The `backend/cmd/seed/` folder is responsible for initializing and populating the database with seed data, primarily for development and testing purposes. It provides functionality to run database migrations, seed the database with initial data, clear existing seed data, and perform a one-time migration to stable UUIDs. The `main.go` file serves as the entry point, handling command-line flags to control the seeding process. It utilizes the `bootstrap` package to establish a database connection and the `seed` package to execute the seeding logic. This folder is crucial for setting up a consistent and reproducible database state.

## Files

### `main.go`
**Role:** Go entry point | **Lines:** 77

The `main.go` file is the entry point for the database seeding application. It parses command-line flags such as `migrate-only`, `clear-only`, and `migrate-uuids` to determine the desired action. It loads environment variables (specifically `DATABASE_URL`) using `godotenv` and initializes the database connection using the `bootstrap.InitDB` function. The file then performs database migrations using `db.AutoMigrate` and calls functions from the `seed` package to seed the database or migrate UUIDs based on the provided flags.

## Stats

- Total files: 1
- Has tests: no
- Has config: no
