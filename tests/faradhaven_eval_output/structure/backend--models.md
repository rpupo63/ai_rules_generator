# Models

**Path:** `backend/models/`
**Purpose:** GORM data models and database schemas

## Overview

The `backend/models/` folder defines the data structures and database schemas for the application using GORM. It contains Go structs that represent various entities in the game, such as characters, beasts, spells, and their relationships. These models are crucial for data persistence and retrieval from the database. The files within this folder define the structure of the data, including fields, data types, and GORM annotations for database mapping, relationships, and constraints. They work together to form a cohesive data model that represents the game world and its entities.

## Files

### `models.go`
**Role:** data model/schema | **Lines:** 71

This file serves as a central point for defining all the GORM models used in the application. The `AllModels` function returns a slice of interfaces, each representing a GORM model. The order of models in the slice is important, as it dictates the order in which tables are created during database migration. Parent tables must be created before child tables with foreign key constraints. This file effectively lists all the data structures that map to database tables and defines the overall database schema.

---

### `archetype.go`
**Role:** source file | **Lines:** 21

This file defines the `Archetype` struct, which represents a subclass or specialization within a character class (e.g., "Path of the Warlord" for the Lorewright class). It includes fields for the archetype's ID, class ID, name, description, and sort order. The `Archetype` struct has a GORM relationship with the `Class` struct, defining a foreign key constraint that ensures data integrity. This model is used to categorize and differentiate character classes, providing a more granular level of character customization.

**Key Exports:**
- `Archetype`

---

### `attack.go`
**Role:** source file | **Lines:** 24

This file defines the `Attack` struct, which represents an attack action for a beast. It includes fields for the attack's ID, beast ID, name, attack bonus, damage type, damage dice, reach, and description. The `Attack` struct has a GORM relationship with the `Beast` struct, defining a foreign key constraint that ensures data integrity. This model is used to define the offensive capabilities of beasts in the game.

**Key Exports:**
- `Attack`

---

### `beast.go`
**Role:** source file | **Lines:** 76

This file defines the `Beast` struct, representing a creature or monster entry in the bestiary. It includes fields for the beast's ID, user ID, name, image URL, size, type, alignment, armor class, hit points, hit dice, speed, ability scores, challenge rating, abilities, actions, legendary actions, and description. It also defines relationships to `User`, `Attack`, and `BeastSkill` structs using GORM, establishing foreign key constraints. The `ParseChallengeRating` function converts the challenge rating string to a float64 for easier comparison.

**Key Exports:**
- `ParseChallengeRating`
- `Beast`

---

### `beast_skill.go`
**Role:** source file | **Lines:** 11

This file defines the `BeastSkill` struct, which represents a structured skill proficiency for a beast. It includes fields for the skill's ID, beast ID, name (e.g., "Stealth", "Perception"), and value. This struct is used to represent the specific skills and their proficiency values for each beast. It has a GORM relationship with the `Beast` struct, defining a foreign key constraint.

**Key Exports:**
- `BeastSkill`

---

### `character.go`
**Role:** source file | **Lines:** 145

This file defines the `Character` struct, which represents a player character in the game. It includes fields for the character's ID, user ID, name, race ID, lineage ID, class ID, archetype ID, level, spellbook IDs, ability scores, current spell points, and class-specific resource tracking fields. It also defines GORM relationships with `User`, `Race`, `Lineage`, `Class`, and `Archetype` structs, establishing foreign key constraints. The `HarvestedAbilities` struct is used to store Lorewright's harvested skills, attacks, and recipes.

**Key Exports:**
- `HarvestedAbilities`
- `Character`

---

### `character_component.go`
**Role:** source file | **Lines:** 19

This file defines the `CharacterComponent` struct, which tracks the quantity of components a character currently possesses. It includes fields for the character ID, component ID, and count. It also defines GORM relationships with the `Character` and `Component` structs, establishing foreign key constraints. This model is used to manage the inventory of components for each character.

**Key Exports:**
- `CharacterComponent`

---

### `character_computed.go`
**Role:** source file | **Lines:** 98

This file defines the `CharacterComputedStats` struct, which holds calculated values for the character sheet. These values are not stored in the database but are computed at runtime based on the character's base stats and modifiers. It includes fields for max HP, current HP, temp HP, armor class, initiative, proficiency bonus, spell save DC, spell attack bonus, max spell points, passive perception, attack bonuses, hit dice tracking, and ability modifiers. The `AbilityModifier` function calculates the modifier for an ability score. The `ComputeStats` function calculates all derived stats for a character.

**Key Exports:**
- `AbilityModifier`
- `ComputeStats`
- `CharacterComputedStats`

---

### `character_effect.go`
**Role:** source file | **Lines:** 43

This file defines the `CharacterEffect` struct, which represents an active effect on a character. It acts as a join table between `Character` and `Effect`, storing additional instance data such as duration, source, stacks, and concentration status. It includes fields for the effect's ID, character ID, effect ID, duration, source, stacks, duration rounds, duration minutes, source character ID, source spell ID, and concentration status. It also defines GORM relationships with `Character` and `Effect` structs, establishing foreign key constraints.

**Key Exports:**
- `CharacterEffect`

---

### `character_link.go`
**Role:** source file | **Lines:** 56

This file defines the `CharacterLink` struct, which represents a bond between two characters. It includes fields for the link's ID, source character ID, target character ID, link type, active status, expiration time, shared effect ID, bonus type, and notes. It also defines GORM relationships with the `Character` struct for both source and target characters, establishing foreign key constraints. The `LinkType` enum defines the possible types of bonds between characters. The `IsExpired` method checks if the link has expired.

**Key Exports:**
- `IsExpired`
- `LinkType`
- `CharacterLink`

---

### `character_resource.go`
**Role:** source file | **Lines:** 42

This file defines the `CharacterResource` struct, which represents a dynamic resource tracked for a character. It includes fields for the resource's ID, character ID, resource key, resource name, current value, max value, rest behavior, and decay behavior. It also defines a GORM relationship with the `Character` struct, establishing a foreign key constraint. This model is used for class-specific resources that don't fit into the standard character fields.

**Key Exports:**
- `CharacterResource`

---

### `character_skill.go`
**Role:** source file | **Lines:** 21

This file defines the `CharacterSkill` model, which represents a character's proficiency in a specific skill. It includes fields for the character's ID, the skill's ID (a string representing a D&D 5e skill), and a boolean indicating proficiency. The `CharacterSkill` model establishes a foreign key relationship with the `Character` model, ensuring that each skill proficiency is associated with a valid character and enabling cascading deletes. The unique index `idx_character_skill` prevents duplicate skill proficiencies for a character.

**Key Exports:**
- `CharacterSkill`

---

### `character_weapon.go`
**Role:** source file | **Lines:** 30

This file defines the `CharacterWeapon` model, representing the relationship between a character and a weapon they possess. It includes fields for IDs of both the character and the weapon, a flag indicating if the weapon is the character's primary weapon, and an optional custom name for the weapon. It also includes relationships to the `Character` and `Weapon` models via foreign keys, with cascading deletes from `Character` to `CharacterWeapon`. Additionally, it has a one-to-many relationship with `WeaponModifier` through the `CharacterWeaponID` foreign key, and specifies the table name as `character_weapons_v2` for GORM.

**Key Exports:**
- `CharacterWeapon`

---

### `class.go`
**Role:** source file | **Lines:** 43

This file defines the `Class` model, representing a character class with its associated data. It includes fields for the class's name, description, hit die, primary ability, and photo URL, as well as D&D-style proficiencies and starting data stored as PostgreSQL arrays. The model also defines relationships to `ClassLevel`, `Component`, `Archetype`, and `ClassStartingEquipmentChoice` models via foreign keys, enabling cascading deletes. The `Levels`, `Components`, `Archetypes`, and `EquipmentChoices` fields are used to preload related data.

**Key Exports:**
- `Class`

---

### `class_component.go`
**Role:** source file | **Lines:** 18

This file defines the `ClassComponent` model, which represents the many-to-many relationship between classes and components. It contains the `ClassID` and `ComponentID` as primary keys, establishing the link between a `Class` and a `Component`. Foreign key relationships with both `Class` and `Component` models are defined, with cascading deletes enabled. This model serves as a join table for the `class_components` table in the database.

**Key Exports:**
- `ClassComponent`

---

### `class_level.go`
**Role:** source file | **Lines:** 56

This file defines the `ClassLevel` model, which represents level-specific data for a character class. It includes fields for the class ID, level, HP gain, proficiency bonus, spellcasting information, class features, ability score improvements, combat upgrades, and shared D&D mechanics. It also defines a one-to-many relationship with the `LevelFeature` model via the `ClassLevelID` foreign key. A foreign key relationship with the `Class` model is also defined, and the `idx_class_level` index ensures that the combination of `ClassID` and `Level` is unique.

**Key Exports:**
- `ClassLevel`

---

### `class_level_resource.go`
**Role:** source file | **Lines:** 23

This file defines the `ClassLevelResource` model, which stores the value of a specific resource at a particular class level. It includes fields for the class level ID, resource key, and the resource value. The `ResourceKey` corresponds to a key defined in `ClassResourceDefinition`. It establishes a foreign key relationship with the `ClassLevel` model, enabling cascading deletes. The `idx_class_level_resource` index ensures the uniqueness of the `ClassLevelID` and `ResourceKey` combination.

**Key Exports:**
- `ClassLevelResource`

---

### `class_resource_definition.go`
**Role:** source file | **Lines:** 37

This file defines the `ClassResourceDefinition` model, which describes a resource type for a character class. It includes fields for the class ID, resource key, display name, category, description, display order, and behavior configuration (e.g., whether the resource is trackable or restored on rests). It establishes a foreign key relationship with the `Class` model, enabling cascading deletes. The `idx_class_resource_def` index ensures the uniqueness of the `ClassID` and `ResourceKey` combination.

**Key Exports:**
- `ClassResourceDefinition`

---

### `class_weapon_requirement.go`
**Role:** source file | **Lines:** 26

This file defines the `ClassWeaponRequirement` model, which specifies when a class requires weapon selection during level-up. It includes fields for the class ID, selection level, modifier type, description, and allowed weapon categories. It establishes a foreign key relationship with the `Class` model, enabling cascading deletes. This model is used to trigger a weapon selection step in the level-up wizard.

**Key Exports:**
- `ClassWeaponRequirement`

---

### `component.go`
**Role:** source file | **Lines:** 23

This file defines the `Component` model, representing a spell-like component available to a class. It includes fields for the component's name, symbol, category, description, element, and tier. The `Category` field uses the `ComponentCategory` enum. This model is used in conjunction with the `ClassComponent` model to define the components available to each class.

**Key Exports:**
- `Component`

---

### `consumption_history.go`
**Role:** source file | **Lines:** 19

This file defines the `ConsumptionHistory` model, which tracks when a Lorewright character harvests a creature. It includes fields for the character ID, creature type, and the timestamp of the harvest. It establishes a foreign key relationship with the `Character` model, enabling cascading deletes. This model is used to enable features like the Warlord's Predator's Strike.

**Key Exports:**
- `ConsumptionHistory`

---

### `corpse.go`
**Role:** source file | **Lines:** 80

This file defines the `Corpse` struct, representing a dead creature in the game world. It includes fields for creature information (name, type, size, challenge rating), position on the map (GridX, GridY), harvestable components (AvailableComponents, ComponentYield), and state tracking (HasBeenHarvested, HasBeenConsumed). It also tracks timing information like `DiedAt` and `ExpiresAt`. The `Corpse` struct has relationships with `GameMap` and `Beast` models, using foreign keys for database relations.

**Key Exports:**
- `IsExpired`
- `MinutesSinceDeath`
- `CanBeHarvested`
- `CanBeConsumed`
- `Corpse`

---

### `effect.go`
**Role:** source file | **Lines:** 19

This file defines the `Effect` struct, which represents a status effect, condition, or special state that can be applied to characters or other game entities. It includes fields for the effect's name, description, category, and mechanics. The `Effect` struct is a standalone model with no explicit relationships to other models defined in this file, but it's likely used in conjunction with other models (e.g., `Character`) through join tables or other association mechanisms.

**Key Exports:**
- `Effect`

---

### `enums.go`
**Role:** source file | **Lines:** 111

This file defines various enums used throughout the models package. It includes `CreatureSize` and `CreatureType` enums, with associated constants for different sizes and types of creatures. It also defines `DamageType` enum with associated constants for different damage types. These enums are used to provide type safety and restrict the possible values for certain fields in other models.

**Key Exports:**
- `CreatureSize`
- `CreatureType`
- `DamageType`
- `ComponentCategory`

---

### `item.go`
**Role:** source file | **Lines:** 35

This file defines the `Item` struct, representing a non-weapon object in the game. It includes fields for item name, description, category, rarity, cost, weight, and effects. It also includes a boolean field `IsConsumable` to indicate whether the item can be consumed. The `Item` struct has a relationship with the `User` model, indicating the item's owner, using a foreign key for database relations.

**Key Exports:**
- `Item`

---

### `level_feature.go`
**Role:** source file | **Lines:** 22

This file defines the `LevelFeature` struct, representing a feature gained at a specific class level. It includes fields for the feature's name, description, and sort order. It also includes foreign keys `ClassLevelID` and `ArchetypeID` to establish relationships with the `ClassLevel` and `Archetype` models, respectively. The `ArchetypeID` is nullable, indicating that some features are available to all archetypes of a class.

**Key Exports:**
- `LevelFeature`

---

### `level_up_history.go`
**Role:** source file | **Lines:** 61

This file defines the `LevelUpHistory` struct, which tracks each level-up event for a character. It stores information about the level gained, choices made during the level-up (skill selections, ASI allocation, spells learned, features gained, archetype selected), and a snapshot of the character's state before the level-up. The snapshot is stored as a JSON object in the `CharacterSnapshot` field. It has relationships with the `Character` and `User` models, using foreign keys for database relations. The `CharacterSnapshotData` struct defines the structure of the JSON data stored in the `CharacterSnapshot` field.

**Key Exports:**
- `LevelUpHistory`
- `CharacterSnapshotData`

---

### `lineage.go`
**Role:** source file | **Lines:** 29

This file defines the `Lineage` struct, which handles sub-races or specific choices like Draconic Ancestry. It includes fields for the lineage's name, description, and damage type. It also includes a JSON field `AbilityScoreBonuses` to store ability score bonuses associated with the lineage. The `Lineage` struct has a relationship with the `Race` model, using a foreign key for database relations. It also has a nested relationship with the `Trait` model through the `LineageTraits` field.

**Key Exports:**
- `Lineage`

---

### `map.go`
**Role:** source file | **Lines:** 33

This file defines the `GameMap` and `MapToken` structs. The `GameMap` struct represents a game map, including its ID, owner, room code, name, background URL, grid dimensions, and tile size. The `MapToken` struct represents a token on the map, including its ID, map ID, character ID, assigned user ID, name, image URL, token type, grid coordinates, size, color, visibility, and initiative order. `GameMap` has a one-to-many relationship with `MapToken`.

**Key Exports:**
- `GameMap`
- `MapToken`

---

### `minion.go`
**Role:** source file | **Lines:** 184

This file defines the `Minion` struct, representing a summoned or created entity controlled by a character. It includes fields for the minion's name, type, combat stats (armor class, max HP, current HP, speed), and type-specific fields (e.g., `ComponentCost` and `TemplateKey` for Ironwright constructs, `AbilityName`, `AbilityDescription`, `AbilityType`, `SourceCreatureType`, and `SlotIndex` for Lorewright echoes). It also includes a boolean field `IsActive` to indicate whether the minion is active. The `Minion` struct has a relationship with the `Character` model, using a foreign key for database relations.

**Key Exports:**
- `GetConstructTemplates`
- `MinionType`
- `Minion`
- `ConstructTemplate`
- `ConstructAction`


## Other Files

- `note.go` - source file, 19 lines
- `race.go` - source file, 38 lines
- `saved_spell.go` - source file, 40 lines
- `seed_metadata.go` - source file, 19 lines
- `spell.go` - source file, 35 lines
- `spell_component.go` - source file, 18 lines
- `starting_equipment.go` - source file, 36 lines
- `trait.go` - source file, 37 lines
- `trait_option.go` - source file, 26 lines
- `user.go` - source file, 27 lines
- `weapon.go` - source file, 52 lines
- `weapon_damage.go` - source file, 25 lines
- `weapon_modifier.go` - source file, 81 lines

## Stats

- Total files: 43
- Has tests: no
- Has config: no
