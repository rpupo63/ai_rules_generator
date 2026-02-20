# Faradhaven_Items

**Path:** `backend/seed/faradhaven_items/`
**Purpose:** data seeding

## Overview

The `backend/seed/faradhaven_items/` folder is responsible for seeding the database with initial data for Faradhaven items and weapons. It defines the structure of items and weapons, provides concrete data for them, and contains the logic to insert this data into the database. The files collaborate by defining data structures (`types.go`), populating those structures with specific item and weapon data (`items.go`, `weapons.go`), and then using that data to seed the database (`seed.go`). This folder is crucial for setting up a functional game environment with pre-defined items and weapons.

## Files

### `types.go`
**Role:** type definitions | **Lines:** 26

This file defines the `WeaponSeed` and `WeaponDamageSeed` structs, which represent the structure of weapons and their damages to be seeded into the database. `WeaponSeed` includes fields like name, description, category, rarity, range type, cost, weight, attack modifier, properties, range, damage dice, and secondary effects. `WeaponDamageSeed` defines the structure for weapon damage information, including damage dice, damage type, and damage category. These structs are used by `weapons.go` to define weapon data and by `seed.go` to create weapon records in the database.

---

### `items.go`
**Role:** source file | **Lines:** 288

This file defines the `ItemSeed` struct, which represents the structure of an item to be seeded into the database. It also contains the `Potions()` function, which returns a slice of `ItemSeed` structs, each representing a specific potion with properties like name, description, category, rarity, cost, weight, effects, and whether it's consumable. This data is used by `seed.go` to create and insert item records into the database. The `ItemSeed` struct is used by the `SeedFaradhavenItems` function in `seed.go` to create item entries.

**Key Exports:**
- `ItemSeed`

---

### `seed.go`
**Role:** source file | **Lines:** 98

This file contains the `SeedFaradhavenItems` function, which is the main entry point for seeding Faradhaven items and weapons into the database. It retrieves weapon data from `weapons.go` using `AllWeapons()`, and item data from `items.go` using `Potions()`. It then iterates through this data, constructs `models.Weapon` and `models.Item` structs, and uses GORM to insert them into the database in batches. It also generates deterministic UUIDs for the items and weapons using the `uuids` package, ensuring that reseeding doesn't break existing references.

**Key Exports:**
- `SeedFaradhavenItems`

---

### `weapons.go`
**Role:** source file | **Lines:** 447

This file provides the concrete data for weapons to be seeded into the database. It contains functions like `TransformativeWeapons()` which returns a slice of `WeaponSeed` structs, each representing a specific weapon with properties like name, description, category, rarity, range type, cost, weight, attack modifier, properties, range, damage dice, and secondary effects. The `WeaponSeed` struct is defined in `types.go`. The data from these functions is used by `seed.go` to create and insert weapon records into the database.

## Stats

- Total files: 4
- Has tests: no
- Has config: no
