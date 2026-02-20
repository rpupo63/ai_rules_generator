# Config

**Path:** `backend/config/`
**Purpose:** Application configuration management

## Overview

The `backend/config/` folder is responsible for managing the application's configuration. It primarily focuses on reading environment variables and providing them as a map for easy access. The `config.go` file handles the core logic for reading and parsing environment variables, as well as providing utility functions to retrieve configuration values with default values. This folder is crucial for adapting the application's behavior based on the environment it's running in, such as development, testing, or production. The `yml/` subfolder likely handles configuration via YAML files, providing an alternative configuration source.

## Subfolders

- **`yml/`** - configuration files (2 files)

## Files

### `config.go`
**Role:** source file | **Lines:** 57

This file is the central component for handling application configuration, specifically environment variables. It defines functions to read all environment variables into a map[string]string. The `New()` function reads the environment and transforms it into a map. Utility functions `GetString()` and `GetInt()` are provided to retrieve configuration values from the map, with the ability to specify default values if the environment variable is not set or cannot be converted to the desired type. This file is independent but its output can be used by any other part of the backend.

**Key Exports:**
- `New`
- `GetString`
- `GetInt`

## Stats

- Total files: 1
- Direct subfolders: 1
- Has tests: no
- Has config: no
