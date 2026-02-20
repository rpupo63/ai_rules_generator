# Batch

**Path:** `backend/seed/batch/`
**Purpose:** project files

## Overview

The `backend/seed/batch/` folder provides utility functions for performing batch database operations, specifically upserts and inserts, using GORM. These functions are designed to efficiently seed or update database tables with large datasets. The folder contains a single file, `upsert.go`, which defines generic functions for upserting records, updating specific columns on conflict, and inserting records in batches. These functions are crucial for the seed package to efficiently populate the database during the application's initialization or testing phases. The `DefaultBatchSize` constant helps control the number of records processed in each batch, optimizing performance.

## Files

### `upsert.go`
**Role:** source file | **Lines:** 56

This file defines generic functions for performing batch database operations using GORM. It includes functions for upserting records with full updates (`UpsertBatchUpdateAll`), upserting with updates to specific columns (`UpsertBatchUpdateColumns`), and inserting records in batches (`InsertBatch`). The `UpsertBatchUpdateAll` function updates all columns of existing records based on the "id" column conflict. The `UpsertBatchUpdateColumns` function allows specifying which columns to update on conflict. The `InsertBatch` function performs simple batch inserts without conflict resolution, suitable for child tables that are cleared before seeding. The file utilizes GORM's `CreateInBatches` function and `clause.OnConflict` to achieve efficient batch processing and conflict handling.

## Stats

- Total files: 1
- Has tests: no
- Has config: no
