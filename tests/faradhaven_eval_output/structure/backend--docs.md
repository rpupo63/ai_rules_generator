# Docs

**Path:** `backend/docs/`
**Purpose:** Project documentation and guides

## Overview

The `backend/docs/` folder serves as the central repository for project documentation, specifically focusing on seed file creation and data modeling. It provides guides and explanations for developers to understand the structure and process of populating the application with initial data. The files within this folder, such as `DESCRIPTION_TO_SEED_PLAN.md` and `RACE_SEED_GUIDE.md`, offer step-by-step instructions and conceptual overviews. These documents are crucial for maintaining consistency and clarity in the data seeding process, ensuring that new developers can quickly onboard and contribute effectively. They outline the data models, relationships, and best practices for creating seed files.

## Files

### `DESCRIPTION_TO_SEED_PLAN.md`
**Role:** documentation | **Lines:** 198

This file outlines the general workflow for converting raw descriptions (e.g., of races or classes) into complete seed files for the Faradhaven application. It details a five-step process: Identify the seed type, Extract relevant fields, Map those fields to seed types, Implement the seed file, and Register and verify the seed. The document provides tables that map description elements to specific fields in the corresponding Go structs. This guide helps developers understand the overall process of creating seed files from source descriptions, ensuring consistency and accuracy in the data seeding process.

---

### `RACE_SEED_GUIDE.md`
**Role:** documentation | **Lines:** 285

This file provides a detailed, step-by-step guide for adding new races to the Faradhaven application using the `faradhaven_races` seed package. It explains the data models involved (Race, Trait, TraitOption, Lineage) and their relationships, including when to use each model. The guide also includes a quick reference for the fields within each model, such as `Name`, `Description`, and `LevelReq`. This document helps developers understand the specific steps and considerations for adding race data, ensuring that the data is structured correctly and consistently.

## Stats

- Total files: 2
- Has tests: no
- Has config: no
