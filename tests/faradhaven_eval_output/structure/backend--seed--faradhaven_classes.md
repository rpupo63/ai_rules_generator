# Faradhaven_Classes

**Path:** `backend/seed/faradhaven_classes/`
**Purpose:** data seeding

## Overview

The `backend/seed/faradhaven_classes/` folder is responsible for defining and seeding the custom character classes for the Faradhaven setting in the application. Each `.go` file in this folder represents a unique character class, defining its attributes, abilities, and progression. The `seed.go` file aggregates these class definitions and provides functions to seed the database with this data. The `types.go` file defines the data structures used to represent the classes and their various properties, ensuring consistency across all class definitions. These files work together to provide a structured and easily maintainable way to define and populate the game's character classes.

## Files

### `types.go`
**Role:** type definitions | **Lines:** 134

This file defines the data structures used to represent the Faradhaven classes and their properties. It includes structs like `EquipmentOptionSeed`, `EquipmentChoiceSeed`, `FeatureSeed`, `ArchetypeSeed`, `WeaponRequirementSeed`, and `ClassLevelSeed`, which are used to define the various aspects of a character class. The `FaradhavenClassSeed` struct, which is not fully shown, likely aggregates these structs to represent a complete class definition. These type definitions are used throughout the other files in this folder to ensure consistency and structure in the class definitions.

---

### `ironwright.go`
**Role:** source file | **Lines:** 171

This file defines the `Ironwright` character class. It contains the `Ironwright()` function, which returns a `FaradhavenClassSeed` struct populated with the Ironwright's specific data, including its description, hit die, proficiencies, equipment choices, level features, and resource definitions. It also defines the `ironwrightLevelFeatures()` and `ironwrightLevelProgression()` functions, which return maps defining the class's features and progression at each level. This file is related to `seed.go` through the `AllClasses()` function, which calls `Ironwright()` to include it in the list of classes to be seeded.

**Key Exports:**
- `Ironwright`

---

### `lorewright.go`
**Role:** source file | **Lines:** 251

This file defines the `Lorewright` character class. The `Lorewright()` function returns a `FaradhavenClassSeed` struct containing the Lorewright's data, such as its description, primary ability, proficiencies, equipment choices, level features, and component pool. It also defines `lorewrightLevelFeatures()` and `lorewrightLevelProgression()` functions, which return maps defining the class's features and progression at each level. Similar to `ironwright.go`, this file is linked to `seed.go` via the `AllClasses()` function, which uses `Lorewright()` to include the Lorewright class in the seeding process.

**Key Exports:**
- `Lorewright`
- `lorewrightArchetypes`

---

### `mutagen.go`
**Role:** source file | **Lines:** 158

This file defines the `Mutagen` character class. The `Mutagen()` function returns a `FaradhavenClassSeed` struct containing the Mutagen's data, including its description, hit die, proficiencies, equipment choices, level features, resource definitions, and component pool. It also defines `mutagenLevelFeatures()` and `mutagenLevelProgression()` functions, which return maps defining the class's features and progression at each level. This file contributes to the seeding process by being called within the `AllClasses()` function in `seed.go`.

**Key Exports:**
- `Mutagen`

---

### `piston_brawler.go`
**Role:** source file | **Lines:** 144

This file defines the `PistonBrawler` character class. The `PistonBrawler()` function returns a `FaradhavenClassSeed` struct populated with the Piston Brawler's specific data, including its description, hit die, proficiencies, equipment choices, level features, resource definitions, and component pool. It also defines `pistonBrawlerLevelFeatures()` and `pistonBrawlerLevelProgression()` functions, which return maps defining the class's features and progression at each level. The `AllClasses()` function in `seed.go` calls `PistonBrawler()` to include this class in the database seeding.

**Key Exports:**
- `PistonBrawler`

---

### `powder_mage.go`
**Role:** source file | **Lines:** 120

This file defines the `PowderMage` character class. The `PowderMage()` function returns a `FaradhavenClassSeed` struct containing the Powder Mage's data, such as its description, primary ability, proficiencies, equipment choices, level features, and archetypes. It also defines `powderMageLevelFeatures()` and `powderMageLevelProgression()` functions, which return maps defining the class's features and progression at each level. This file contributes to the database seeding process through the `AllClasses()` function in `seed.go`, which calls `PowderMage()`.

**Key Exports:**
- `PowderMage`

---

### `rift_weaver.go`
**Role:** source file | **Lines:** 95

This file defines the `RiftWeaver` character class. The `RiftWeaver()` function returns a `FaradhavenClassSeed` struct containing the Rift Weaver's data, including its description, hit die, proficiencies, equipment choices, level features, resource definitions, and component pool. It also defines `riftWeaverLevelFeatures()` and `riftWeaverLevelProgression()` functions, which return maps defining the class's features and progression at each level. This class is added to the list of classes to be seeded via the `AllClasses()` function in `seed.go`.

**Key Exports:**
- `RiftWeaver`

---

### `sanguinist.go`
**Role:** source file | **Lines:** 134

This file defines the `Sanguinist` character class. The `Sanguinist()` function returns a `FaradhavenClassSeed` struct containing the Sanguinist's data, including its description, hit die, proficiencies, equipment choices, level features, resource definitions, and component pool. It also defines `sanguinistLevelFeatures()` and `sanguinistLevelProgression()` functions, which return maps defining the class's features and progression at each level. This file contributes to the seeding process by being called within the `AllClasses()` function in `seed.go`.

**Key Exports:**
- `Sanguinist`

---

### `seed.go`
**Role:** source file | **Lines:** 431

This file contains the core logic for seeding the Faradhaven classes into the database. The `AllClasses()` function returns a slice of `FaradhavenClassSeed` structs by calling the individual class definition functions (e.g., `Mutagen()`, `Ironwright()`). The file also defines the `ClassComponentLink` struct and its table name, representing the many-to-many relationship between classes and components. The `proficiencyByLevel()` function calculates the proficiency bonus based on the character level. The `SeedFaradhavenClasses()` function takes a database connection and seeds the classes, their level progressions, features, archetypes, equipment choices, and components, handling potential errors during the seeding process.

**Key Exports:**
- `AllClasses`
- `proficiencyByLevel`
- `maxSpellPointsByLevel`
- `abilityScoreImprovementByLevel`
- `SeedFaradhavenClasses`
- `SeedFaradhavenClassesIfEmpty`
- `BackfillAbilityScoreImprovements`
- `ClassComponentLink`

---

### `vapor_blade.go`
**Role:** source file | **Lines:** 118

This file defines the `VaporBlade` character class. The `VaporBlade()` function returns a `FaradhavenClassSeed` struct populated with the Vapor Blade's specific data, including its description, hit die, proficiencies, equipment choices, level features, resource definitions, and component pool. It also defines `vaporBladeLevelFeatures()` and `vaporBladeLevelProgression()` functions, which return maps defining the class's features and progression at each level. The `AllClasses()` function in `seed.go` calls `VaporBlade()` to include this class in the database seeding.

**Key Exports:**
- `VaporBlade`

## Stats

- Total files: 10
- Has tests: no
- Has config: no
