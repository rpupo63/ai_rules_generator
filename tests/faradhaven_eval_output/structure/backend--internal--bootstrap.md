# Bootstrap

**Path:** `backend/internal/bootstrap/`
**Purpose:** Application initialization and bootstrapping

## Overview

The `bootstrap` folder is responsible for initializing the application's core components, primarily the database connection. It handles loading environment variables, establishing a connection to the PostgreSQL database using GORM, configuring database connection pooling, and setting up necessary database extensions. The `bootstrap.go` file contains the core logic for database initialization. This folder ensures that the application has a properly configured and accessible database connection before it starts serving requests.

## Files

### `bootstrap.go`
**Role:** source file | **Lines:** 79

This file initializes the database connection using GORM and configures connection pooling. The `InitDB` function takes a data source name (DSN) as input, connects to the PostgreSQL database, configures logging, and sets up database extensions. It also configures connection pooling parameters such as `MaxIdleConns`, `MaxOpenConns`, and `ConnMaxLifetime`. The `setupExtensions` function, also defined in this file, is responsible for enabling specific PostgreSQL extensions required by the application.

**Key Exports:**
- `InitDB`
- `setupExtensions`
- `LoadEnv`

## Stats

- Total files: 1
- Has tests: no
- Has config: no
