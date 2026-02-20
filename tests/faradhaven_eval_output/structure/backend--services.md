# Services

**Path:** `backend/services/`
**Purpose:** Core business logic services

## Overview

The `backend/services/` folder houses the core business logic of the application. It contains service implementations that handle various domain-specific operations, such as corpse management, effect application, harvesting, character leveling, and component interpretation. These services encapsulate complex logic and interact with the database through repositories defined in the `database` package. The files in this folder collaborate to provide a cohesive set of functionalities, ensuring data consistency and enforcing business rules. They are crucial for the application's functionality, providing the backend logic for the API endpoints.

## Files

### `component_interpreter_service.go`
**Role:** service implementation | **Lines:** 165

This file implements the `ComponentInterpreterService`, which is responsible for parsing component strings and converting them into `SpellResult` structs. It uses `database.ComponentRepo` and `database.EffectRepo` to retrieve component and effect data from the database. The `Interpret` function is the main entry point, taking a slice of component names and returning a `SpellResult` containing damage instances, range, area of effect, effects, saving throw information, and a description. This service is essential for dynamically generating spell effects based on component combinations.

**Key Exports:**
- `NewComponentInterpreterService`
- `Interpret`
- `DamageInstance`
- `SpellResult`
- `ComponentInterpreterService`

---

### `corpse_service.go`
**Role:** service implementation | **Lines:** 175

This file implements the `CorpseService`, which manages corpse-related operations, including creation and retrieval. It relies on the `database.CorpseRepo` for database interactions. The `CreateCorpse` function handles the creation of new corpse entries, while other functions likely handle retrieving corpses based on various criteria. The service also handles default values for corpse attributes like size and component yield. This service is important for managing in-game corpses that can be harvested for components.

**Key Exports:**
- `NewCorpseService`
- `HarvestCorpse`
- `ConsumeCorpse`
- `GetCorpse`
- `GetCorpses`
- `DeleteCorpse`
- `CleanupExpiredCorpses`
- `CorpseService`
- `CreateCorpseRequest`
- `HarvestResult`

---

### `effect_service.go`
**Role:** service implementation | **Lines:** 277

This file implements the `EffectService`, which handles the application, management, and tracking of effects on characters. It uses `database.CharacterEffectRepo` and `database.EffectRepo` to interact with the database. Key functions include `ApplyEffect`, which applies a new effect to a character, and functions for handling effect stacking, duration, and expiration. The `Tick` function is likely used to decrement effect durations and identify expired effects. This service is crucial for managing status effects and other temporary modifications to character attributes.

**Key Exports:**
- `NewEffectService`
- `RemoveEffect`
- `ModifyStacks`
- `TickDuration`
- `BreakConcentration`
- `GetActiveEffects`
- `GetActiveEffect`
- `ClearAllEffects`
- `HasEffect`
- `GetEffectsBySource`

---

### `harvesting_service.go`
**Role:** service implementation | **Lines:** 181

This file implements the `HarvestingService`, which handles the logic for the Lorewright's Visceral Psychometry, allowing characters to harvest abilities from beasts. It depends on `database.CharacterRepository`, `database.BeastRepository`, `database.ConsumptionHistoryRepository`, and `database.ClassRepository` to retrieve character, beast, consumption history, and class data. The service provides functions for determining which abilities can be harvested from a given beast and calculating the Fracture DC, which determines if a Lorewright must make a saving throw. This service is specific to the Lorewright class and its unique harvesting mechanic.

**Key Exports:**
- `NewHarvestingService`
- `ConfirmHarvest`
- `HarvestingService`
- `HarvestableAbility`
- `HarvestableAbilitiesResponse`
- `ConfirmHarvestRequest`

---

### `hp_service.go`
**Role:** service implementation | **Lines:** 284

This file extends the `LevelUpService` (even though the file name suggests it should be a separate service) with HP-related functionalities, specifically for updating a character's HP. It uses the `CharacterRepo` and `componentRepo` to find characters and components. The `UpdateHP` function updates the character's current HP and includes logic specific to the Sanguinist class, such as granting "Unstable Ichor" components when HP is gained through certain actions. This file tightly integrates HP management with the leveling and class-specific mechanics.

**Key Exports:**
- `UpdateHP`
- `SetTempHP`
- `UseHitDice`
- `ShortRest`
- `LongRest`
- `ensureHPInitialized`
- `UseHitDiceResult`

---

### `level_down_service.go`
**Role:** service implementation | **Lines:** 107

This file extends the `LevelUpService` with the functionality to revert a character to their previous level. It relies on the `CharacterRepo` and `historyRepo` to retrieve character data and level-up history. The `LevelDown` function finds the level-up history for the current level, parses the character snapshot stored in the history, and restores the character's attributes to the previous state. This service is crucial for allowing players to undo level-up decisions.

**Key Exports:**
- `LevelDown`

---

### `level_history_service.go`
**Role:** service implementation | **Lines:** 107

This file extends the `LevelUpService` with functionalities to retrieve level-up history and preview the next level's features. It uses the `CharacterRepo`, `classRepo`, and `historyRepo` to retrieve character, class, and level-up history data. The `GetLevelHistory` function returns all level-up history entries for a character. The `GetLevelUpPreview` function calculates and returns the features and abilities that will be available at the next level. This service provides players with information about their character's progression and future options.

**Key Exports:**
- `GetLevelHistory`
- `GetLevelUpPreview`

---

### `level_up_service.go`
**Role:** service implementation | **Lines:** 351

This file implements the `LevelUpService`, which handles the complex logic of leveling up a character. It uses multiple repositories, including `CharacterRepo`, `classRepo`, `historyRepo`, `archetypeRepo`, `weaponRepo`, and `componentRepo`, to retrieve character, class, level-up history, archetype, weapon, and component data. The service provides functions for validating level-up requirements, allocating attribute points, selecting archetypes, and saving the character's state. It also interacts with the `ResourceService`. This service is central to the character progression system.

**Key Exports:**
- `NewLevelUpService`
- `filterFeaturesByArchetype`
- `findClassLevelWithFeatures`
- `LevelUpService`
- `LevelUpRequest`
- `LevelUpResponse`
- `LevelUpPreview`
- `WeaponSelectionInfo`

---

### `link_service.go`
**Role:** service implementation | **Lines:** 45

This file implements the `LinkService`, which manages relationships between characters. It uses `database.CharacterLinkRepository` to interact with the database. The `CreateLink` function creates a new character link, `RemoveLink` deletes a link, and `GetLinks` retrieves links associated with a character. This service is likely used to represent relationships such as family, friends, or enemies between characters in the game world.

**Key Exports:**
- `NewLinkService`
- `CreateLink`
- `RemoveLink`
- `GetLinks`
- `LinkService`
- `linkService`

---

### `madness_service.go`
**Role:** service implementation | **Lines:** 80

This file implements the `MadnessService`, responsible for handling Lorewright's Madness Die rolls. It depends on `database` package for character and class data access via `CharacterRepository` and `ClassRepository` interfaces. The `RollMadness` function simulates the die roll, retrieves the character's class level, and determines the madness effect based on the roll. The `MadnessRollResult` struct encapsulates the outcome of the roll, including the character ID, roll value, die type, and the resulting effect.

**Key Exports:**
- `NewMadnessService`
- `MadnessService`
- `MadnessRollResult`

---

### `minion_service.go`
**Role:** service implementation | **Lines:** 435

This file implements the `MinionService`, which manages minions (constructs, echoes, etc.) for characters. It relies on the `database` package, specifically `MinionRepo`, `CharacterRepo`, `ClassRepo`, and `ComponentRepo` for data access. The service provides functionality to create constructs based on templates, including setting custom names and storing metadata about actions and recipe components. The `CreateConstructRequest` struct defines the expected input for construct creation.

**Key Exports:**
- `NewMinionService`
- `validateAndDeductComponents`
- `DestroyConstruct`
- `CreateDrone`
- `StoreEcho`
- `ActivateEcho`
- `DeactivateEcho`
- `GetMinions`
- `GetMinion`
- `UpdateMinionHP`

---

### `notoriety_service.go`
**Role:** service implementation | **Lines:** 31

This file defines the `NotorietyService` and its interface, which is responsible for updating a character's notoriety based on changes to their SanguineMP (Morality Points) and SanguineBR (Brutality Rating). It uses the `database` package's `CharacterRepository` to retrieve and update character data. The `UpdateNotoriety` function calculates the new notoriety value and persists the changes to the database.

**Key Exports:**
- `NewNotorietyService`
- `UpdateNotoriety`
- `NotorietyService`
- `notorietyService`

---

### `resource_service.go`
**Role:** service implementation | **Lines:** 163

This file implements the `ResourceService`, which handles class-specific resource calculations and restoration for characters. It depends on the `database` package, specifically `ClassRepo` and `CharacterResourceRepo`, for accessing class resource definitions and character resource data. The `InitializeCharacterResources` function creates `CharacterResource` entries for all trackable resources defined by a character's class, using level-based resource values for initial maximums.

**Key Exports:**
- `NewResourceService`
- `UpdateCharacterResourcesForLevel`
- `GetResourceValue`
- `GetResourceMaxValue`
- `GetAllCharacterResources`
- `DeductResource`
- `RestoreClassResources`
- `ResourceService`

---

### `s3_service.go`
**Role:** service implementation | **Lines:** 69

This file implements the `S3Service`, which handles file uploads to Amazon S3. It uses the `aws-sdk-go-v2` library to interact with S3. The `UploadFile` function takes a multipart file, generates a unique key, uploads the file to the configured S3 bucket, and returns the URL of the uploaded file. It retrieves AWS credentials and bucket name from environment variables and constructs the S3 URL.

**Key Exports:**
- `NewS3Service`
- `UploadFile`
- `S3Service`

---

### `saved_spell_service.go`
**Role:** service implementation | **Lines:** 190

This file implements the `SavedSpellService`, which manages saved spell combinations (Speed Dials) for characters. It depends on the `database` package, specifically `SavedSpellRepo`, `CharacterRepo`, and `ClassRepo` for data access. The `SaveSpell` function allows characters to save spell combinations to specific slots, validating slot limits and persisting the spell data, including associated components and costs. The `SaveSpellRequest` struct defines the expected input for saving a spell.

**Key Exports:**
- `NewSavedSpellService`
- `CalculateBlueprintCost`
- `CastSavedSpell`
- `GetSpeedDial`
- `ClearSlot`
- `ResetUsesOnRest`
- `SavedSpellService`
- `SaveSpellRequest`

---

### `lorewright_helpers.go`
**Role:** source file | **Lines:** 24

This file provides helper functions specifically for the Lorewright class, particularly for calculating the Fracture DC when harvesting creatures. The `CalculateFractureDC` function determines if a Lorewright must make a saving throw against The Fracture based on their level and the creature's challenge rating. It returns a boolean indicating whether a save is required and the DC for the check. This file encapsulates the specific logic for the Lorewright's harvesting mechanic.

**Key Exports:**
- `CalculateFractureDC`

## Stats

- Total files: 16
- Has tests: no
- Has config: no
