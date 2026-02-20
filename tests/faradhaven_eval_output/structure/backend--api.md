# Api

**Path:** `backend/api/`
**Purpose:** HTTP API endpoints and handlers

## Overview

The `backend/api/` folder defines the HTTP API endpoints for the backend application. It handles routing, request parsing, response formatting, and interacts with the database and services layers. Each file within this folder typically represents a specific resource or feature, such as authentication, characters, or beasts. Handlers are responsible for receiving HTTP requests, validating data, calling appropriate business logic, and returning responses in JSON format. The folder relies heavily on the `database` package for data access and the `models` package for data structures, and uses `github.com/go-chi/chi/v5` for routing.

## Files

### `middleware.go`
**Role:** middleware | **Lines:** 212

This file defines middleware functions for the API, including authentication and request logging. The `authMiddleware` struct handles authentication by verifying the presence and validity of a Bearer token in the Authorization header. It depends on the `database` package for accessing the `UserRepository` to validate the token. The `authenticate` method is the core middleware function that checks the token and sets the user ID in the request context. It uses a `Responder` to handle error responses.

---

### `routes.go`
**Role:** route definitions | **Lines:** 189

This file defines the API routes using the `chi` router. It groups routes into public (no authentication required) and protected (authentication required) sections. It uses handler functions defined in other files (e.g., `authHandler`, `characterHandler`, `weaponHandler`) to handle specific routes. The `setupFrontendRoutes` function sets up all the routes, applying middleware like `ColoredHTTPLoggingMiddleware` and `authMiddleware` where appropriate. It relies on the `routeHandlers` struct (defined in `types.go`) to hold instances of all the handlers.

---

### `types.go`
**Role:** type definitions | **Lines:** 565

This file defines various data structures and type aliases used throughout the API. It defines the `routeHandlers` struct, which aggregates all the individual handler structs (e.g., `authHandler`, `userHandler`, `characterHandler`). It also defines request and response types for various API endpoints, such as `ErrorResponse` and `CreateMapRequest`. These types are used for request validation, data serialization, and documentation purposes.

---

### `auth_handler.go`
**Role:** source file | **Lines:** 206

This file defines the `authHandler` struct and its associated methods for handling authentication-related API endpoints, specifically login and registration. It depends on the `database.UserRepository` for user data access and uses `bcrypt` for password hashing. The handler defines request and response structs for login and registration (`LoginRequest`, `LoginResponse`, `RegisterRequest`). It also uses a `Responder` to format and send HTTP responses.

**Key Exports:**
- `newAuthHandler`
- `register`
- `generateSessionToken`
- `hashPassword`
- `EnsureFirstUserExists`
- `authHandler`
- `LoginRequest`
- `LoginResponse`
- `RegisterRequest`

---

### `beast_handler.go`
**Role:** source file | **Lines:** 298

This file defines the `beastHandler` struct and its methods for handling API endpoints related to beasts (monsters). It depends on `database.BeastRepository` and `database.AttackRepository` for data access. The handler provides functions for retrieving all beasts (`getAllBeasts`) and retrieving a specific beast by ID, including its attacks (`getBeast`). It uses `github.com/go-chi/chi/v5` to extract the beast ID from the URL parameters and returns responses in JSON format.

**Key Exports:**
- `newBeastHandler`
- `getBeast`
- `getBeastsByUser`
- `createBeast`
- `updateBeast`
- `deleteBeast`
- `beastHandler`

---

### `character_compendium_handler.go`
**Role:** source file | **Lines:** 87

This file defines handler methods related to character compendium data, specifically races and classes, within the `characterHandler` struct. It provides endpoints for retrieving all races (`getAllRaces`), retrieving a race by ID with its traits (`getRaceByID`), and retrieving all classes (`getAllClasses`). It relies on `database.RaceRepository` and `database.ClassRepository` for data access. The handler uses `github.com/go-chi/chi/v5` to extract the race ID from the URL parameters.

**Key Exports:**
- `getAllRaces`
- `getRaceByID`
- `getAllClasses`
- `getClassByID`

---

### `character_creation_handler.go`
**Role:** source file | **Lines:** 260

This file defines handler methods within the `characterHandler` struct for character creation options. Specifically, it implements the `getCreationOptions` function, which retrieves all races and classes with full details for the character creation wizard. It depends on `database.RaceRepository` and `database.ClassRepository` to fetch the race and class data. The handler constructs a `CreationOptionsResponse` struct containing the races, classes, and a default points maximum value, and returns it as a JSON response.

**Key Exports:**
- `getCreationOptions`
- `createCharacter`

---

### `character_effect_handler.go`
**Role:** source file | **Lines:** 261

This file defines the `characterEffectHandler` struct and its methods for handling API endpoints related to character effects. It depends on the `services.EffectService` to retrieve active effects for a given character. The `GetActiveEffects` method retrieves the character ID from the URL parameters, calls the `effectService` to get the active effects, and then formats the response into a slice of `CharacterEffectResponse` structs before sending it as a JSON response.

**Key Exports:**
- `newCharacterEffectHandler`
- `ApplyEffect`
- `ModifyStacks`
- `RemoveEffect`
- `TickDuration`
- `BreakConcentration`
- `characterEffectHandler`

---

### `character_handler.go`
**Role:** source file | **Lines:** 1043

This file defines the `characterHandler` struct and its associated methods for handling API endpoints related to character management. It depends on various repositories including `database.CharacterRepository`, `database.RaceRepository`, `database.ClassRepository`, `database.CharacterResourceRepository`, `database.ItemRepository`, `database.WeaponRepository`, and `database.SpellRepository`. It also utilizes services like `services.ResourceService`, `services.NotorietyService`, `services.S3Service`, and `services.ComponentInterpreterService`. The handler provides a wide range of functionalities, including creating, retrieving, updating, and deleting characters, managing character resources, equipment, and spells, and handling character images.

**Key Exports:**
- `newCharacterHandler`
- `abilityMod`
- `primaryAbilityMod`
- `getAllCharacters`
- `getCharacter`
- `restSpellPoints`
- `getCharactersByUser`
- `updateCharacter`
- `deleteCharacter`
- `updateBackstory`

---

### `character_sheet_handler.go`
**Role:** source file | **Lines:** 255

This file defines handler methods within the `characterHandler` struct for retrieving a fully calculated character sheet. The `getCharacterSheet` method retrieves the character ID from the URL parameters and fetches the character data using `characterRepo.FindByIDWithSkills`. It then preloads related data such as weapons, modifiers, and items. It also checks user authorization before returning the character sheet as a JSON response.

**Key Exports:**
- `getCharacterSheet`

---

### `component_handler.go`
**Role:** source file | **Lines:** 69

This file defines the `componentHandler` struct and its methods for handling API endpoints related to spell system components. It depends on `database.ComponentRepo` for data access. The handler provides functions for retrieving all components (`getAllComponents`), retrieving a component by ID (`getComponentByID`), and retrieving components by category (`getComponentsByCategory`). It uses `github.com/go-chi/chi/v5` to extract the component ID and category from the URL parameters and returns responses in JSON format.

**Key Exports:**
- `newComponentHandler`
- `getComponentByID`
- `getComponentsByCategory`
- `componentHandler`

---

### `context.go`
**Role:** source file | **Lines:** 45

This file defines functions for managing context values related to user and organization IDs. It defines a `keyType` for defining context keys and provides functions like `ctxWithUserID`, `ctxWithOrganizationID`, `ctxGetUserID`, and `ctxGetOrganizationID` to set and retrieve these values from the context. These functions are used to pass user and organization information between middleware and handler functions, enabling authentication and authorization checks.

**Key Exports:**
- `ctxWithUserID`
- `ctxGetOrganizationID`
- `ctxGetStringValue`
- `keyType`

---

### `corpse_handler.go`
**Role:** source file | **Lines:** 210

This file defines the `corpseHandler` struct and its methods for handling API endpoints related to corpses (dead entities). It depends on `services.CorpseService`, `database.CharacterRepo`, and `database.ComponentRepo`. The `GetCorpses` method retrieves all corpses, optionally filtered by `map_id`. It calls the `corpseService` to get the corpse data and returns it as a JSON response. The handler also includes methods for creating, retrieving, updating, and deleting corpses.

**Key Exports:**
- `newCorpseHandler`
- `GetCorpse`
- `CreateCorpse`
- `HarvestCorpse`
- `ConsumeCorpse`
- `DeleteCorpse`
- `corpseHandler`

---

### `effect_handler.go`
**Role:** source file | **Lines:** 50

This file defines the `effectHandler` struct and its associated methods for handling HTTP requests related to game effects. It depends on the `database` package for data access, specifically the `EffectRepository` interface. The handler provides endpoints for retrieving all effects (`getAllEffects`) and retrieving a specific effect by its ID (`getEffectByID`). It uses `chi.URLParam` to extract the effect ID from the request URL and `uuid.Parse` to validate it. The handler uses helper functions `respondJSON` and `respondError` to send responses.

**Key Exports:**
- `newEffectHandler`
- `getEffectByID`
- `effectHandler`

---

### `handlers.go`
**Role:** source file | **Lines:** 103

This file initializes all the HTTP handlers for the API. The `initializeHandlers` function takes a `database.Database` interface as input, initializes various services (ResourceService, NotorietyService, S3Service, LevelUpService, HarvestingService, MadnessService, EffectService, LinkService), and returns a `routeHandlers` struct containing the initialized handlers. It acts as a central point for wiring up the database layer, service layer, and API handler layer. The file also handles the initialization of S3 service, logging an error if it fails.

---

### `harvest_handler.go`
**Role:** source file | **Lines:** 102

This file defines the `harvestHandler` struct and its methods for handling HTTP requests related to harvesting abilities from beasts. It depends on the `database` package for data access (specifically `CharacterRepository`) and the `services` package for the `HarvestingService`. The `getHarvestableAbilities` method handles the GET request to retrieve harvestable abilities for a given beast ID. It extracts the beast ID from the URL using `chi.URLParam`, retrieves the user ID from the request context using `ctxGetUserID`, and then uses the `HarvestingService` to fetch the harvestable abilities.

**Key Exports:**
- `newHarvestHandler`
- `confirmHarvest`
- `harvestHandler`

---

### `item_handler.go`
**Role:** source file | **Lines:** 50

This file defines the `itemHandler` struct and its associated methods for handling HTTP requests related to game items. It depends on the `database` package for data access, specifically the `ItemRepository` interface. The handler provides endpoints for retrieving all items (`getAllItems`) and retrieving a specific item by its ID (`getItemByID`). It uses `chi.URLParam` to extract the item ID from the request URL and `uuid.Parse` to validate it. The handler uses helper functions `respondJSON` and `respondError` to send responses.

**Key Exports:**
- `newItemHandler`
- `getItemByID`
- `itemHandler`

---

### `level_handler.go`
**Role:** source file | **Lines:** 520

This file defines the `levelHandler` struct and its methods for handling HTTP requests related to character leveling. It depends on the `database` package for data access (specifically `ClassRepo`, `CharacterResourceRepository`, `BeastRepository`, `ConsumptionHistoryRepository`) and the `services` package for the `LevelUpService`. It includes functions to handle level up requests, build class resources, and retrieve available level up actions. The `buildClassResources` function aggregates resource definitions, level values, and character state into a response-ready slice of `ClassResourceResponse`.

**Key Exports:**
- `newLevelHandler`
- `levelDown`
- `getLevelHistory`
- `getLevelUpPreview`
- `updateHP`
- `setTempHP`
- `useHitDice`
- `shortRest`
- `longRest`
- `levelHandler`

---

### `link_handler.go`
**Role:** source file | **Lines:** 92

This file defines the `linkHandler` struct and its methods for handling HTTP requests related to character links. It depends on the `services` package for the `LinkService`. The `createLink` method handles the POST request to create a new link between two characters. It extracts the source character ID from the URL using `chi.URLParam`, decodes the request body into a `CreateLinkRequest` struct, and then uses the `LinkService` to create the link.

**Key Exports:**
- `newLinkHandler`
- `removeLink`
- `getLinks`
- `linkHandler`
- `CreateLinkRequest`

---

### `madness_handler.go`
**Role:** source file | **Lines:** 54

This file defines the `madnessHandler` struct and its methods for handling HTTP requests related to character madness. It depends on the `services` package for the `MadnessService`. The `rollMadness` method handles the POST request to roll for madness for a given character. It extracts the character ID from the URL using `chi.URLParam`, retrieves the user ID from the request context using `ctxGetUserID`, and then uses the `MadnessService` to roll for madness.

**Key Exports:**
- `newMadnessHandler`
- `madnessHandler`

---

### `map_handler.go`
**Role:** source file | **Lines:** 546

This file defines the `mapHandler` struct and its methods for handling HTTP requests related to game maps. It depends on the `database` package for data access, specifically the `MapRepo`. The handler provides endpoints for creating a new map (`createMap`), retrieving a map by ID, updating a map, and deleting a map. It uses `chi.URLParam` to extract the map ID from the request URL and `uuid.Parse` to validate it. It also retrieves the user ID from the request context using `ctxGetUserID` to enforce authorization.

**Key Exports:**
- `newMapHandler`
- `getMap`
- `getMapByRoom`
- `getUserMaps`
- `updateMap`
- `deleteMap`
- `addToken`
- `updateToken`
- `deleteToken`
- `getInitiative`

---

### `mechanics_handler.go`
**Role:** source file | **Lines:** 215

This file defines the `MechanicsHandler` struct and its methods for handling HTTP requests related to game mechanics, specifically rolling on effect tables. It directly uses the `gorm.DB` for database access. The `RollTable` method handles the POST request to roll on a specific effect table and apply the result to a character. It extracts the character ID from the URL using `chi.URLParam`, decodes the request body into a `RollTableRequest` struct, and then determines the category and source based on the table name before applying the effect.

**Key Exports:**
- `NewMechanicsHandler`
- `MutagenCast`
- `GetActiveEffects`
- `RemoveEffect`
- `MechanicsHandler`

---

### `minion_handler.go`
**Role:** source file | **Lines:** 240

This file defines the `minionHandler` type and its associated methods for handling HTTP requests related to minions. It depends on the `services.MinionService` to interact with the underlying data. The handler includes methods for retrieving minions by character ID, with optional filtering by minion type, and retrieving a specific minion by its ID. It uses `respondJSON` and `respondError` (defined in `respond.go`) to send responses and utilizes `chi.URLParam` to extract the character ID from the request URL.

**Key Exports:**
- `newMinionHandler`
- `GetMinion`
- `CreateMinion`
- `UpdateMinionHP`
- `ActivateMinion`
- `DeactivateMinion`
- `DeleteMinion`
- `GetConstructTemplates`
- `minionHandler`

---

### `note_handler.go`
**Role:** source file | **Lines:** 68

This file defines the `noteHandler` type and its methods for handling HTTP requests related to shared notes. It depends on `database.NoteRepository` for data access. The handler provides methods for retrieving all notes and creating new notes. The `createNote` function parses the request body, extracts note details, and uses the repository to add the note to the database. It uses `respondJSON` and `respondError` (defined in `respond.go`) for sending responses.

**Key Exports:**
- `newNoteHandler`
- `createNote`
- `noteHandler`

---

### `resource_handler.go`
**Role:** source file | **Lines:** 229

This file defines the `resourceHandler` type and its methods for handling HTTP requests related to character resources. It depends on `database.CharacterResourceRepo` for data access. The handler includes methods for retrieving all resources associated with a character ID and retrieving a specific resource by its key and character ID. It uses `respondJSON` and `respondError` (defined in `respond.go`) to send responses and `chi.URLParam` to extract the character ID and resource key from the request URL.

**Key Exports:**
- `newResourceHandler`
- `GetResource`
- `CreateResource`
- `SpendResource`
- `GainResource`
- `DeleteResource`
- `resourceHandler`

---

### `respond.go`
**Role:** source file | **Lines:** 178

This file provides helper functions for constructing HTTP responses, specifically `respondJSON` and `respondError`. `respondJSON` sets the Content-Type header to `application/json` and marshals the provided data to JSON before writing it to the response writer. `respondError` sets the appropriate HTTP status code and returns a JSON response containing an error message. It also includes a `Responder` struct which encapsulates a logger for more robust error handling and response size limiting.

**Key Exports:**
- `NewResponder`
- `WriteJSON`
- `WriteError`
- `WriteTimeoutError`
- `WriteValidationError`
- `WithTimeoutCheck`
- `CheckContextTimeout`
- `wrapDatabaseError`
- `respondJSON`
- `respondError`

---

### `server.go`
**Role:** source file | **Lines:** 243

This file creates and configures the HTTP server. It defines the `Server` struct, which embeds an `http.Server` and includes a startup time. The `NewServer` function initializes the router using `newRouter`, sets up timeouts, and returns a configured `Server` instance. The `newRouter` function is responsible for setting up all the API endpoints and middleware. It reads the port from the environment variables, defaulting to 8080 if not set.

**Key Exports:**
- `NewServer`
- `withStartupTime`
- `newRouter`
- `ShutdownGracefully`
- `formatUptime`
- `rootHandler`
- `healthcheckHandler`
- `Server`
- `router`

---

### `spell_handler.go`
**Role:** source file | **Lines:** 286

This file defines the `spellHandler` type and its methods for handling HTTP requests related to spells. It depends on `database.SpellRepository` for data access. The handler provides methods for retrieving all spells and retrieving a specific spell by its ID. The `getSpell` function parses the spell ID from the URL, retrieves the spell from the repository, and returns it as a JSON response. It uses `respondJSON` and `respondError` (defined in `respond.go`) for sending responses.

**Key Exports:**
- `newSpellHandler`
- `getSpell`
- `getSpellsByUser`
- `getSpellsByCharacter`
- `createSpell`
- `updateSpell`
- `deleteSpell`
- `spellHandler`

---

### `user_handler.go`
**Role:** source file | **Lines:** 252

This file defines the `userHandler` type and its methods for handling HTTP requests related to users. It depends on `database.UserRepository` for data access. The handler provides methods for retrieving all users and retrieving a specific user by their ID. The `getUser` function parses the user ID from the URL, retrieves the user from the repository, and returns it as a JSON response. It also checks if the authenticated user has permission to access the requested user's data. It uses `respondJSON` and `respondError` (defined in `respond.go`) for sending responses.

**Key Exports:**
- `newUserHandler`
- `getUser`
- `getUserFull`
- `createUser`
- `updateUser`
- `setActiveCharacter`
- `deleteUser`
- `userHandler`

---

### `weapon_handler.go`
**Role:** source file | **Lines:** 29

This file defines the `weaponHandler` type and its method for handling HTTP requests to retrieve all weapons. It depends on `database.WeaponRepo` for data access. The `getAllWeapons` function retrieves all weapons from the repository and returns them as a JSON response. It uses `respondJSON` and `respondError` (defined in `respond.go`) for sending responses.

**Key Exports:**
- `newWeaponHandler`
- `weaponHandler`

## Stats

- Total files: 30
- Has tests: no
- Has config: no
