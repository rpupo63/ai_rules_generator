# Yml

**Path:** `backend/config/yml/`
**Purpose:** configuration files

## Overview

The `backend/config/yml/` folder houses YAML configuration files that govern the behavior of the backend application. These files define settings related to various aspects of the application, such as HTTP server timeouts and database connection parameters. The application reads these YAML files during startup to configure its components. These configurations are crucial for customizing the application's behavior without modifying the source code, enabling easier deployment and management. The files within this folder are essential for setting up the application's environment and operational parameters.

## Files

### `http.yml`
**Role:** configuration | **Lines:** 14

This file configures the HTTP server settings for the backend application. It defines timeout values for reading requests (`READ_TIMEOUT_SECONDS`), writing responses (`WRITE_TIMEOUT_SECONDS`), and managing idle connections (`IDLE_TIMEOUT_SECONDS`). It also configures the `MAXAGE` setting for CORS (Cross-Origin Resource Sharing), which controls how long a browser can cache CORS preflight requests. These settings directly impact the performance and security of the HTTP server. The application reads these values during initialization to configure the HTTP server's behavior.

---

### `token.yml`
**Role:** configuration | **Lines:** 0

## Stats

- Total files: 2
- Has tests: no
- Has config: yes
