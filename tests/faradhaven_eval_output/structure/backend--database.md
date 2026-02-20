# Database

**Path:** `backend/database/`
**Purpose:** Data Access Layer (DAL) and GORM repositories

## Overview

The `backend/database/` folder serves as the Data Access Layer (DAL) for the Go backend application. It houses GORM repositories responsible for interacting with the database. Each file in this folder typically represents a specific data model (e.g., `Character`, `Beast`, `Class`) and provides an interface and its implementation for performing CRUD operations on that model. These repositories abstract the database interactions from the business logic, promoting separation of concerns and making the application more maintainable. The repositories use GORM to simplify database operations and ensure data consistency.

## Files

### `archetype_repo.go`
**Role:** source file | **Lines:** 37

This file defines the `ArchetypeRepository` interface and its implementation, `ArchetypeRepo`, for accessing and manipulating `Archetype` data in the database. It provides methods for finding archetypes by class ID (`FindByClassID`) and by ID (`FindByID`). The `FindByClassID` method also orders the results by `SortOrder`. The `ArchetypeRepo` struct holds a GORM database connection, and the `NewArchetypeRepo` function creates a new instance of the repository.

**Key Exports:**
- `NewArchetypeRepo`
- `FindByID`
- `ArchetypeRepository`
- `ArchetypeRepo`

---

### `attack_repo.go`
**Role:** source file | **Lines:** 47

This file defines the `AttackRepository` interface and its implementation, `AttackRepo`, for managing `Attack` data. It includes methods for retrieving attacks associated with a specific beast (`FindByBeastID`), adding a new attack (`Add`), updating an existing attack (`Update`), and deleting an attack by its ID (`Delete`). The `AttackRepo` struct holds a GORM database connection, and the `NewAttackRepo` function creates a new `AttackRepo` instance. The `Add` method sets the `CreatedAt` timestamp before inserting the new attack.

**Key Exports:**
- `NewAttackRepo`
- `Add`
- `Update`
- `Delete`
- `AttackRepository`
- `AttackRepo`

---

### `beast_repo.go`
**Role:** source file | **Lines:** 102

This file defines the `BeastRepository` interface and its implementation, `BeastRepo`, for interacting with `Beast` data. It provides methods for retrieving all beasts (`FindAll`), finding a beast by ID (`FindByID`), finding a beast by ID with its associated attacks (`FindByIDWithAttacks`), finding a beast by ID with its relations (`FindByIDWithRelations`), finding beasts belonging to a specific user (`FindByUserID`), finding beasts belonging to a specific user with their attacks (`FindByUserIDWithAttacks`), adding a new beast (`Add`), updating an existing beast (`Update`), and deleting a beast (`Delete`). The `BeastRepo` struct holds a GORM database connection, and the `NewBeastRepo` function creates a new `BeastRepo` instance. The `Add` method sets the `CreatedAt` timestamp before inserting the new beast.

**Key Exports:**
- `NewBeastRepo`
- `FindByID`
- `FindByIDWithAttacks`
- `FindByIDWithRelations`
- `FindByUserID`
- `FindByUserIDWithAttacks`
- `Add`
- `Update`
- `Delete`
- `BeastRepository`

---

### `character_effect_repo.go`
**Role:** source file | **Lines:** 111

This file defines the `CharacterEffectRepository` interface and its implementation, `CharacterEffectRepo`, for managing `CharacterEffect` data. It provides methods for retrieving effects associated with a character (`FindByCharacterID`), finding an effect by ID (`FindByID`), adding a new effect (`Add`), updating an existing effect (`Update`), deleting an effect by ID (`Delete`), deleting all effects for a character (`DeleteByCharacterID`), finding concentration effects (`FindConcentrationEffects`), and finding effects originating from a specific character (`FindBySourceCharacter`). The `CharacterEffectRepo` struct holds a GORM database connection, and the `NewCharacterEffectRepo` function creates a new `CharacterEffectRepo` instance. The `Add` method sets the `CreatedAt` timestamp before inserting the new effect.

**Key Exports:**
- `NewCharacterEffectRepo`
- `FindByID`
- `Add`
- `Update`
- `Delete`
- `DeleteByCharacterID`
- `FindConcentrationEffects`
- `FindBySourceCharacter`
- `FindByEffectAndCharacter`
- `DecrementDurationRounds`

---

### `character_link_repo.go`
**Role:** source file | **Lines:** 109

This file defines the `CharacterLinkRepository` interface and its implementation, `CharacterLinkRepo`, for managing relationships between characters represented by `CharacterLink` data. It offers methods for retrieving links involving a character as either source or target (`FindByCharacterID`), finding links where a character is the source (`FindBySourceCharacter`), finding links where a character is the target (`FindByTargetCharacter`), finding a link by ID (`FindByID`), adding a new link (`Add`), updating an existing link (`Update`), and deleting a link by ID (`Delete`). The `CharacterLinkRepo` struct holds a GORM database connection, and the `NewCharacterLinkRepo` function creates a new `CharacterLinkRepo` instance.

**Key Exports:**
- `NewCharacterLinkRepo`
- `FindBySourceCharacter`
- `FindByTargetCharacter`
- `FindActiveByType`
- `FindByID`
- `FindExisting`
- `Add`
- `Update`
- `Delete`
- `DeleteExpired`

---

### `character_repo.go`
**Role:** source file | **Lines:** 176

This file defines the `CharacterRepository` interface and its implementation, `CharacterRepo`, for managing `Character` data. It includes methods for retrieving all characters (`FindAll`), finding a character by ID (`FindByID`), finding a character by ID with skills (`FindByIDWithSkills`), finding a character by ID with relations (`FindByIDWithRelations`), finding characters belonging to a specific user (`FindByUserID`), adding a new character (`Add`), updating an existing character (`Update`), deleting a character (`Delete`), replacing skill proficiencies for a character (`ReplaceSkillProficiencies`), updating the count of a component for a character (`UpdateComponentCount`), and getting the underlying GORM database instance (`GetDB`). The `CharacterRepo` struct holds a GORM database connection, and the `NewCharacterRepo` function creates a new `CharacterRepo` instance.

**Key Exports:**
- `NewCharacterRepo`
- `FindByID`
- `FindByIDWithSkills`
- `FindByIDWithRelations`
- `FindByUserID`
- `Add`
- `Update`
- `Delete`
- `ReplaceSkillProficiencies`
- `UpdateComponentCount`

---

### `character_resource_repo.go`
**Role:** source file | **Lines:** 130

This file defines the `CharacterResourceRepository` interface and its implementation, `CharacterResourceRepo`, for managing `CharacterResource` data. It provides methods for retrieving resources associated with a character (`FindByCharacterID`), finding a specific resource by character ID and key (`FindByCharacterAndKey`), adding a new resource (`Add`), updating an existing resource (`Update`), deleting a resource by ID (`Delete`), deleting all resources for a character (`DeleteByCharacterID`), and updating the current value of a resource (`UpdateCurrentValue`). The `CharacterResourceRepo` struct holds a GORM database connection, and the `NewCharacterResourceRepo` function creates a new `CharacterResourceRepo` instance. The `Add` method sets the `CreatedAt` and `UpdatedAt` timestamps before inserting the new resource.

**Key Exports:**
- `NewCharacterResourceRepo`
- `FindByCharacterAndKey`
- `Add`
- `Update`
- `Delete`
- `DeleteByCharacterID`
- `UpdateCurrentValue`
- `ProcessRestoration`
- `CharacterResourceRepository`
- `CharacterResourceRepo`

---

### `class_repo.go`
**Role:** source file | **Lines:** 157

This file defines the `ClassRepository` interface and its implementation, `ClassRepo`, for managing `Class` data. It provides methods for retrieving all classes (`FindAll`), finding a class by ID (`FindByID`), finding a class by ID with levels (`FindByIDWithLevels`), finding a class by name (`FindByName`), finding a specific class level (`FindLevelByClassAndLevel`), finding equipment options by IDs (`FindEquipmentOptionsByIDs`), finding weapon requirements (`FindWeaponRequirementByClassAndLevel`), finding resource definitions (`FindResourceDefinitionsByClassID`), finding level resources (`FindLevelResourcesByClassLevel`, `FindLevelResourcesByClassAndLevel`), getting a level resource map (`GetLevelResourceMap`), getting a level resource value (`GetLevelResourceValue`), adding a new class (`Add`), and adding a new level (`AddLevel`). The `ClassRepo` struct holds a GORM database connection, and the `NewClassRepo` function creates a new `ClassRepo` instance.

**Key Exports:**
- `NewClassRepo`
- `FindByID`
- `FindByIDWithLevels`
- `FindByName`
- `FindLevelByClassAndLevel`
- `FindEquipmentOptionsByIDs`
- `Add`
- `AddLevel`
- `FindWeaponRequirementByClassAndLevel`
- `FindResourceDefinitionsByClassID`

---

### `component_repo.go`
**Role:** source file | **Lines:** 56

This file defines the `ComponentRepo` struct, which provides methods for accessing and manipulating `Component` data in the database. It includes functions for retrieving all components (`GetAllComponents`), retrieving a component by ID (`GetComponentByID`), retrieving components by category (`GetComponentsByCategory`), retrieving components by names (`GetComponentsByNames`), and finding a component by name (`FindByName`). The `ComponentRepo` struct holds a GORM database connection, and the `NewComponentRepo` function creates a new instance of the repository.

**Key Exports:**
- `NewComponentRepo`
- `GetComponentByID`
- `GetComponentsByCategory`
- `GetComponentsByNames`
- `FindByName`
- `ComponentRepo`

---

### `consumption_history_repo.go`
**Role:** source file | **Lines:** 40

This file defines the `ConsumptionHistoryRepository` interface and its implementation, `ConsumptionHistoryRepo`, for managing `ConsumptionHistory` data. It provides methods for creating a new consumption history record (`Create`) and finding the most recent consumption history record for a character and creature type within a specified time frame (`FindRecentByCharacterAndType`). The `ConsumptionHistoryRepo` struct holds a GORM database connection, and the `NewConsumptionHistoryRepo` function creates a new `ConsumptionHistoryRepo` instance. The `Create` method sets the `HarvestedAt` timestamp before inserting the new record.

**Key Exports:**
- `NewConsumptionHistoryRepo`
- `FindRecentByCharacterAndType`
- `ConsumptionHistoryRepository`
- `ConsumptionHistoryRepo`

---

### `corpse_repo.go`
**Role:** source file | **Lines:** 97

This file defines the `CorpseRepository` interface and its implementation `CorpseRepo`. `CorpseRepo` is responsible for handling database interactions related to the `models.Corpse` struct, using GORM. It provides methods for finding, adding, updating, and deleting corpse records. The `NewCorpseRepo` function creates a new instance of the repository, taking a GORM database connection as input.

**Key Exports:**
- `NewCorpseRepo`
- `FindByMapID`
- `FindByID`
- `FindHarvestable`
- `FindConsumable`
- `Add`
- `Update`
- `Delete`
- `DeleteExpired`
- `DeleteByMapID`

---

### `database.go`
**Role:** source file | **Lines:** 177

This file defines the `Database` struct, which serves as a central point for accessing all repositories. It initializes each repository (e.g., `UserRepo`, `CharacterRepo`, `CorpseRepo`) with a shared GORM database connection. The `New` function creates a new `Database` instance, instantiating all repositories and associating them with the provided GORM database instance. This promotes a single point of access for all data operations.

**Key Exports:**
- `New`
- `UserRepo`
- `DB`
- `Database`

---

### `effect_repo.go`
**Role:** source file | **Lines:** 44

This file defines the `EffectRepository` interface and its implementation `EffectRepo`. `EffectRepo` manages database interactions for `models.Effect` entities using GORM. It includes methods for finding all effects, finding an effect by ID, and finding an effect by name. The `NewEffectRepo` function instantiates the repository, requiring a GORM database connection.

**Key Exports:**
- `NewEffectRepo`
- `FindByID`
- `FindByName`
- `EffectRepository`
- `EffectRepo`

---

### `item_repo.go`
**Role:** source file | **Lines:** 49

This file defines the `ItemRepository` interface and its implementation `ItemRepo`. The `ItemRepo` is responsible for managing database operations related to `models.Item` entities, utilizing GORM. It provides methods for finding all items, finding an item by ID, adding a new item, updating an existing item, and deleting an item. The `NewItemRepo` function creates a new `ItemRepo` instance, taking a GORM database connection as input.

**Key Exports:**
- `NewItemRepo`
- `FindByID`
- `Add`
- `Update`
- `Delete`
- `ItemRepository`
- `ItemRepo`

---

### `level_up_history_repo.go`
**Role:** source file | **Lines:** 71

This file defines the `LevelUpHistoryRepository` interface and its implementation `LevelUpHistoryRepo`. `LevelUpHistoryRepo` handles database interactions for `models.LevelUpHistory` records using GORM. It provides methods for finding level-up history by character ID, by character ID and level, and the latest level-up history for a character, as well as methods for adding and deleting records. The `NewLevelUpHistoryRepo` function creates a new instance of the repository, requiring a GORM database connection.

**Key Exports:**
- `NewLevelUpHistoryRepo`
- `FindByCharacterAndLevel`
- `FindLatestByCharacter`
- `Add`
- `Delete`
- `DeleteByCharacterAndLevel`
- `LevelUpHistoryRepository`
- `LevelUpHistoryRepo`

---

### `map_repo.go`
**Role:** source file | **Lines:** 95

This file defines the `MapRepo` struct, which is responsible for handling database interactions related to `models.GameMap` entities using GORM. It provides methods for creating, retrieving (by ID or room code, including preloading tokens), updating, and deleting game maps. The `NewMapRepo` function creates a new instance of the repository, taking a GORM database connection as input.

**Key Exports:**
- `NewMapRepo`
- `GetMapByID`
- `GetMapByRoomCode`
- `GetMapsByOwner`
- `UpdateMap`
- `DeleteMap`
- `AddToken`
- `UpdateToken`
- `GetTokenByID`
- `DeleteToken`

---

### `minion_repo.go`
**Role:** source file | **Lines:** 100

This file defines the `MinionRepository` interface and its implementation `MinionRepo`. `MinionRepo` manages database operations for `models.Minion` entities using GORM. It includes methods for finding minions by character ID, by character ID and type, and by ID, as well as methods for adding, updating, and deleting minions. The `NewMinionRepo` function creates a new instance of the repository, requiring a GORM database connection.

**Key Exports:**
- `NewMinionRepo`
- `FindByCharacterAndType`
- `FindByID`
- `Add`
- `Update`
- `Delete`
- `DeleteByCharacterID`
- `CountByCharacterAndType`
- `FindActiveByCharacterAndType`
- `FindEchoBySlot`

---

### `note_repo.go`
**Role:** source file | **Lines:** 56

This file defines the `NoteRepository` interface and its implementation `NoteRepo`. `NoteRepo` handles database interactions for `models.SharedNote` entities using GORM. It provides methods for finding all notes, finding a note by ID, adding a new note, updating an existing note, and deleting a note. The `NewNoteRepo` function creates a new instance of the repository, taking a GORM database connection as input.

**Key Exports:**
- `NewNoteRepo`
- `FindByID`
- `Add`
- `Update`
- `Delete`
- `NoteRepository`
- `NoteRepo`

---

### `race_repo.go`
**Role:** source file | **Lines:** 62

This file defines the `RaceRepository` interface and its implementation `RaceRepo`. `RaceRepo` manages database interactions for `models.Race` and `models.Lineage` entities using GORM. It provides methods for finding all races, finding a race by ID (with or without traits), finding a race by name, and finding a lineage by ID with traits. The `NewRaceRepo` function creates a new instance of the repository, requiring a GORM database connection.

**Key Exports:**
- `NewRaceRepo`
- `FindByID`
- `FindByIDWithTraits`
- `FindLineageByIDWithTraits`
- `FindByName`
- `RaceRepository`
- `RaceRepo`

---

### `saved_spell_repo.go`
**Role:** source file | **Lines:** 85

This file defines the `SavedSpellRepository` interface and its implementation `SavedSpellRepo`. `SavedSpellRepo` manages database operations for `models.SavedSpell` entities using GORM. It includes methods for finding saved spells by character ID, by character ID and slot, and by ID, as well as methods for adding, updating, and deleting saved spells. The `NewSavedSpellRepo` function creates a new instance of the repository, requiring a GORM database connection.

**Key Exports:**
- `NewSavedSpellRepo`
- `FindByCharacterAndSlot`
- `FindByID`
- `Add`
- `Update`
- `Delete`
- `DeleteByCharacterID`
- `ResetUsesOnRest`
- `SavedSpellRepository`
- `SavedSpellRepo`

---

### `spell_repo.go`
**Role:** source file | **Lines:** 107

This file defines the `SpellRepository` interface and its implementation `SpellRepo`. The `SpellRepo` struct provides data access methods for the `models.Spell` model, using GORM to interact with the database. It includes methods for finding spells by ID, user ID, and character ID, as well as methods for adding, updating, and deleting spells. The repository also handles preloading the `Components` relationship of a spell, indicating a many-to-many relationship with a component model (not shown in this file but assumed to exist).

**Key Exports:**
- `NewSpellRepo`
- `FindByID`
- `FindByUserID`
- `FindByCharacterID`
- `Add`
- `ReplaceComponents`
- `replaceComponentsTx`
- `Update`
- `Delete`
- `SpellRepository`

---

### `user_repo.go`
**Role:** source file | **Lines:** 102

This file defines the `UserRepository` interface and its implementation `UserRepo`. The `UserRepo` struct provides data access methods for the `models.User` model, utilizing GORM for database interactions. It includes methods for finding users by ID, email, and token, along with methods for adding, updating, and deleting users. The `FindByIDWithAllRelations` function suggests that the User model has relationships to other models that are eagerly loaded.

**Key Exports:**
- `NewUserRepo`
- `FindByID`
- `FindByIDWithAllRelations`
- `FindByEmail`
- `FindByToken`
- `Add`
- `Update`
- `Delete`
- `UserRepository`
- `UserRepo`

---

### `weapon_repo.go`
**Role:** source file | **Lines:** 62

This file defines the `WeaponRepository` interface and its implementation `WeaponRepo`. The `WeaponRepo` struct provides data access methods for the `models.Weapon` model, using GORM for database operations. It includes methods for finding weapons by ID, category, and a list of IDs, as well as a method to retrieve all weapons. The repository preloads the `Damages` relationship, indicating a one-to-many relationship between `Weapon` and a `Damage` model (not defined in this file).

**Key Exports:**
- `NewWeaponRepo`
- `FindByID`
- `FindByCategories`
- `FindByIDs`
- `WeaponRepository`
- `WeaponRepo`

## Stats

- Total files: 23
- Has tests: no
- Has config: no
