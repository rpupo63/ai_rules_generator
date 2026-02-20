# Faradhaven_Races

**Path:** `backend/seed/faradhaven_races/`
**Purpose:** data seeding

## Overview

The `backend/seed/faradhaven_races/` folder is responsible for providing seed data for various playable races in the Faradhaven setting. Each `.go` file within this folder defines a specific race, encapsulating its attributes like name, description, traits, and ability score bonuses. These files work together by providing a collection of race definitions that can be used to populate the game's database or other data structures during the application's initialization or testing phases. The data is structured using `FaradhavenRaceSeed` and `TraitSeed` structs, facilitating a consistent format for race information. This folder is crucial for ensuring that the game world has a diverse and well-defined set of playable races.

## Files

### `types.go`
**Role:** type definitions | **Lines:** 37

This file defines the data structures used to represent race and trait information for seeding the Faradhaven setting. It defines three key structs: `FaradhavenRaceSeed`, `TraitSeed`, and `TraitOptionSeed`. `FaradhavenRaceSeed` represents the overall race data, including name, description, ability score bonuses, languages, and a list of traits. `TraitSeed` represents a single racial trait, including its name, description, level requirement, action type, and any associated options. `TraitOptionSeed` represents a specific option within a trait, such as different types of wings or shrouds. The other files in this directory, such as `tiefling.go` and `warforged.go`, use these structs to define specific race data.

---

### `aasimar.go`
**Role:** source file | **Lines:** 78

This file defines the Aasimar race and its associated traits. The `Aasimar()` function returns a `FaradhavenRaceSeed` struct populated with the Aasimar's specific data, including its name, description, photo URL, creature type, size, base speed, ability score bonuses, languages, traits, and component names. The `aasimarTraits()` function returns a slice of `TraitSeed` structs, each representing a unique trait of the Aasimar race, such as "Celestial Resistance" and "Healing Hands". This file is self-contained and doesn't directly depend on other files in the folder, although it uses the shared `FaradhavenRaceSeed` and `TraitSeed` structures.

**Key Exports:**
- `Aasimar`

---

### `boggart.go`
**Role:** source file | **Lines:** 53

This file defines the Boggart race and its associated traits. The `Boggart()` function returns a `FaradhavenRaceSeed` struct, which contains the Boggart's race-specific information, including its name, description, photo URL, creature type, size, base speed, languages, and traits. The `boggartTraits()` function returns a slice of `TraitSeed` structs, each representing a trait of the Boggart race, such as "Goblinoid Heritage" and "Nimble Escape". Similar to `aasimar.go`, this file is self-contained and relies on the shared `FaradhavenRaceSeed` and `TraitSeed` structures for data consistency.

**Key Exports:**
- `Boggart`

---

### `changeling.go`
**Role:** source file | **Lines:** 33

This file defines the Changeling race and its associated traits. The `Changeling()` function returns a `FaradhavenRaceSeed` struct containing the Changeling's race-specific data, including name, description, photo URL, creature type, size, base speed, languages, bonus language count, and traits. The `changelingTraits()` function returns a slice of `TraitSeed` structs, each representing a trait of the Changeling race, such as "Changeling Instincts" and "Shape-Shifter". This file is independent and uses the common `FaradhavenRaceSeed` and `TraitSeed` structures.

**Key Exports:**
- `Changeling`

---

### `dhampir.go`
**Role:** source file | **Lines:** 62

This file defines the Dhampir race and its associated traits. The `Dhampir()` function returns a `FaradhavenRaceSeed` struct populated with the Dhampir's specific data, including its name, description, photo URL, creature type, size, base speed, languages, bonus language count, and traits. The `dhampirTraits()` function returns a slice of `TraitSeed` structs, each representing a unique trait of the Dhampir race, such as "Darkvision" and "Vampiric Bite". The `dhampirVampiricBiteOptions()` function defines the options available for the "Vampiric Bite" trait. This file is self-contained and uses the shared `FaradhavenRaceSeed`, `TraitSeed`, and `TraitOptionSeed` structures.

**Key Exports:**
- `Dhampir`

---

### `dragonborn.go`
**Role:** source file | **Lines:** 78

This file defines the Dragonborn race and its associated traits. The `Dragonborn()` function returns a `FaradhavenRaceSeed` struct containing the Dragonborn's race-specific data, including name, description, photo URL, creature type, size, base speed, ability score bonuses, languages, traits, and component names. The `dragonbornTraits()` function returns a slice of `TraitSeed` structs, each representing a trait of the Dragonborn race, such as "Draconic Ancestry" and "Breath Weapon". The `dragonbornAncestryOptions()` function defines the options for the "Draconic Ancestry" trait. This file is self-contained and uses the shared `FaradhavenRaceSeed`, `TraitSeed`, and `TraitOptionSeed` structures.

**Key Exports:**
- `Dragonborn`

---

### `dwarf.go`
**Role:** source file | **Lines:** 52

This file defines the Dwarf race and its associated traits. The `Dwarf()` function returns a `FaradhavenRaceSeed` struct containing the Dwarf's race-specific data, including name, description, photo URL, creature type, size, base speed, ability score bonuses, languages, and traits. The `dwarfTraits()` function returns a slice of `TraitSeed` structs, each representing a trait of the Dwarf race, such as "Darkvision" and "Stonecunning". This file is self-contained and uses the shared `FaradhavenRaceSeed` and `TraitSeed` structures.

**Key Exports:**
- `Dwarf`

---

### `elf.go`
**Role:** source file | **Lines:** 95

This file defines the Elf race and its associated traits. The `Elf()` function returns a `FaradhavenRaceSeed` struct containing the Elf's race-specific data, including name, description, photo URL, creature type, size, base speed, ability score bonuses, languages, traits, and component names. The `elfTraits()` function returns a slice of `TraitSeed` structs, each representing a trait of the Elf race, such as "Darkvision" and "Elven Lineage". The `elfLineageOptions()` and `elfKeenSensesOptions()` functions define the options for the "Elven Lineage" and "Keen Senses" traits, respectively. This file is self-contained and uses the shared `FaradhavenRaceSeed`, `TraitSeed`, and `TraitOptionSeed` structures.

**Key Exports:**
- `Elf`

---

### `faerie.go`
**Role:** source file | **Lines:** 62

This file defines the Faerie race and its associated traits. The `Faerie()` function returns a `FaradhavenRaceSeed` struct containing the Faerie's race-specific data, including name, description, photo URL, creature type, size, base speed, languages, traits, and component names. The `faerieTraits()` function returns a slice of `TraitSeed` structs, each representing a trait of the Faerie race, such as "Fairy Magic" and "Flight". The `faerieSpellcastingAbilityOptions()` and `faerieOriginOptions()` functions define the options for the "Fairy Magic" and "Faerie Origin" traits, respectively. This file is self-contained and uses the shared `FaradhavenRaceSeed`, `TraitSeed`, and `TraitOptionSeed` structures.

**Key Exports:**
- `Faerie`

---

### `flamekin.go`
**Role:** source file | **Lines:** 60

This file defines the Flamekin race and its associated traits. The `Flamekin()` function returns a `FaradhavenRaceSeed` struct containing the Flamekin's race-specific data, including name, description, photo URL, creature type, size, base speed, languages, traits, and component names. The `flamekinTraits()` function returns a slice of `TraitSeed` structs, each representing a trait of the Flamekin race, such as "Darkvision" and "Reach to the Blaze". The `flamekinSpellcastingOptions()` function defines the spellcasting ability options for the "Reach to the Blaze" trait. This file is self-contained and uses the shared `FaradhavenRaceSeed`, `TraitSeed`, and `TraitOptionSeed` structures.

**Key Exports:**
- `Flamekin`

---

### `gnome.go`
**Role:** source file | **Lines:** 59

This file defines the Gnome race and its associated traits. The `Gnome()` function returns a `FaradhavenRaceSeed` struct containing the Gnome's race-specific data, including name, description, photo URL, creature type, size, base speed, ability score bonuses, languages, traits, and component names. The `gnomeTraits()` function returns a slice of `TraitSeed` structs, each representing a trait of the Gnome race, such as "Darkvision" and "Gnomish Cunning". The `gnomeLineageOptions()` function defines the lineage options for the "Gnomish Lineage" trait. This file is self-contained and uses the shared `FaradhavenRaceSeed`, `TraitSeed`, and `TraitOptionSeed` structures.

**Key Exports:**
- `Gnome`

---

### `goliath.go`
**Role:** source file | **Lines:** 73

This file defines the `Goliath` race for the Faradhaven setting. It contains the `Goliath()` function which returns a `FaradhavenRaceSeed` struct populated with the Goliath race's data, including its name, description, photo URL, creature type, size, base speed, languages, and traits. The `goliathTraits()` function returns a slice of `TraitSeed` structs specific to the Goliath race, such as "Giant Ancestry" and "Large Form". The `goliathGiantAncestryOptions()` function defines the options available for the "Giant Ancestry" trait, linking to specific component combinations.

**Key Exports:**
- `Goliath`

---

### `halfling.go`
**Role:** source file | **Lines:** 48

This file defines the `Halfling` race for the Faradhaven setting. It contains the `Halfling()` function which returns a `FaradhavenRaceSeed` struct populated with the Halfling race's data, including its name, description, photo URL, creature type, size, base speed, ability score bonuses, languages, and traits. The `halflingTraits()` function returns a slice of `TraitSeed` structs specific to the Halfling race, such as "Brave", "Halfling Nimbleness", "Luck", and "Naturally Stealthy".

**Key Exports:**
- `Halfling`

---

### `human.go`
**Role:** source file | **Lines:** 47

This file defines the `Human` race for the Faradhaven setting. It contains the `Human()` function which returns a `FaradhavenRaceSeed` struct populated with the Human race's data, including its name, description, photo URL, creature type, size, base speed, ability score bonuses, languages, bonus language count, and traits. The `humanTraits()` function returns a slice of `TraitSeed` structs specific to the Human race, such as "Resourceful", "Skillful", and "Versatile".

**Key Exports:**
- `Human`

---

### `kalashtar.go`
**Role:** source file | **Lines:** 47

This file defines the `Kalashtar` race for the Faradhaven setting. It contains the `Kalashtar()` function which returns a `FaradhavenRaceSeed` struct populated with the Kalashtar race's data, including its name, description, photo URL, creature type, size, base speed, languages, bonus language count, and traits. The `kalashtarTraits()` function returns a slice of `TraitSeed` structs specific to the Kalashtar race, such as "Dual Mind", "Mental Discipline", "Mind Link", and "Severed from Dreams".

**Key Exports:**
- `Kalashtar`

---

### `khoravar.go`
**Role:** source file | **Lines:** 54

This file defines the `Khoravar` race for the Faradhaven setting. It contains the `Khoravar()` function which returns a `FaradhavenRaceSeed` struct populated with the Khoravar race's data, including its name, description, photo URL, creature type, size, base speed, languages, traits, and component names. The `khoravarTraits()` function returns a slice of `TraitSeed` structs specific to the Khoravar race, such as "Darkvision", "Fey Ancestry", "Fey Gift", "Lethargy Resilience", and "Skill Versatility".

**Key Exports:**
- `Khoravar`

---

### `lorwyn_changeling.go`
**Role:** source file | **Lines:** 46

This file defines the `LorwynChangeling` race for the Faradhaven setting. It contains the `LorwynChangeling()` function which returns a `FaradhavenRaceSeed` struct populated with the Lorwyn Changeling race's data, including its name, description, photo URL, creature type, size, base speed, languages, bonus language count, and traits. The `lorwynChangelingTraits()` function returns a slice of `TraitSeed` structs specific to the Lorwyn Changeling race, such as "Shape Self", "Darkvision", "Delightful Imitator", and "Unpredictable Movement".

**Key Exports:**
- `LorwynChangeling`

---

### `orc.go`
**Role:** source file | **Lines:** 47

This file defines the `Orc` race for the Faradhaven setting. It contains the `Orc()` function which returns a `FaradhavenRaceSeed` struct populated with the Orc race's data, including its name, description, photo URL, creature type, size, base speed, ability score bonuses, languages, and traits. The `orcTraits()` function returns a slice of `TraitSeed` structs specific to the Orc race, such as "Adrenaline Rush", "Darkvision", and "Relentless Endurance".

**Key Exports:**
- `Orc`

---

### `rimekin.go`
**Role:** source file | **Lines:** 60

This file defines the `Rimekin` race for the Faradhaven setting. It contains the `Rimekin()` function which returns a `FaradhavenRaceSeed` struct populated with the Rimekin race's data, including its name, description, photo URL, creature type, size, base speed, languages, traits, and component names. The `rimekinTraits()` function returns a slice of `TraitSeed` structs specific to the Rimekin race, such as "Darkvision", "Cold Resistance", and "Cold Fire Magic". The `rimekinSpellcastingOptions()` function defines the spellcasting ability options for the "Cold Fire Magic" trait.

**Key Exports:**
- `Rimekin`

---

### `seed.go`
**Role:** source file | **Lines:** 184

This file contains the main seeding logic for Faradhaven races. The `AllRaces()` function returns a slice of `FaradhavenRaceSeed` structs, aggregating all the race definitions from other files in this directory (e.g., `Goliath()`, `Halfling()`). It also defines the `RaceComponentLink` struct, which represents the join table between races and components, and implements the `TableName()` method to specify the table name in the database. The `SeedRaces()` function takes a database connection as input, iterates through the races returned by `AllRaces()`, and seeds the database with the race data, including associated traits, trait options, and component links. It uses helper functions like `createRace`, `createTraits`, `createTraitOptions`, and `createComponentLinks` to handle the database interactions. This file depends on the `models` package for the database models and the `batch` and `uuids` packages for batch processing and UUID generation, respectively.

**Key Exports:**
- `AllRaces`
- `SeedFaradhavenRaces`
- `RaceComponentLink`

---

### `shifter.go`
**Role:** source file | **Lines:** 74

This file defines the `Shifter` race for the Faradhaven setting. It contains the `Shifter()` function which returns a `FaradhavenRaceSeed` struct populated with the Shifter race's data, including its name, description, photo URL, creature type, size, base speed, languages, bonus language count, and traits. The `shifterTraits()` function returns a slice of `TraitSeed` structs specific to the Shifter race, such as "Bestial Instincts", "Darkvision", and "Shifting". The `shifterBestialInstinctsOptions()` and `shifterShiftingOptions()` functions define the options available for the "Bestial Instincts" and "Shifting" traits, respectively.

**Key Exports:**
- `Shifter`

---

### `tiefling.go`
**Role:** source file | **Lines:** 62

This file defines the `Tiefling` race for the Faradhaven setting. It contains the `Tiefling()` function, which returns a `FaradhavenRaceSeed` struct populated with the Tiefling's specific data, including its name, description, photo URL, size, speed, ability score bonuses, languages, and traits. The file also defines helper functions `tieflingTraits()` and `tieflingFiendishLegacyOptions()` which return slices of `TraitSeed` and `TraitOptionSeed` respectively, defining the Tiefling's unique racial traits and trait options. This file relies on the `types.go` file for the definitions of `FaradhavenRaceSeed`, `TraitSeed`, and `TraitOptionSeed`.

**Key Exports:**
- `Tiefling`

---

### `warforged.go`
**Role:** source file | **Lines:** 51

This file defines the `Warforged` race for the Faradhaven setting. It contains the `Warforged()` function, which returns a `FaradhavenRaceSeed` struct populated with the Warforged's specific data, including its name, description, photo URL, size, speed, languages, bonus language count, and traits. The file also defines a helper function `warforgedTraits()` which returns a slice of `TraitSeed`, defining the Warforged's unique racial traits. This file relies on the `types.go` file for the definitions of `FaradhavenRaceSeed` and `TraitSeed`.

**Key Exports:**
- `Warforged`

## Stats

- Total files: 23
- Has tests: no
- Has config: no
