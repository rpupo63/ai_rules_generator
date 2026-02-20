# Project Root

**Path:** `root/`
**Purpose:** project root

## Overview

This folder represents the root directory of the project, serving as the central hub connecting the frontend, backend, and documentation. It contains configuration files like `.gitignore` to manage version control and documentation files that provide guidance on the project's architecture, coding conventions, and deprecation plans. These files are crucial for setting up the development environment, maintaining code quality, and ensuring consistent project understanding among developers. The root folder acts as the entry point for understanding the overall project structure and accessing key resources.

## Subfolders

- **`backend/`** - Go application (11 files)
- **`docs/`** - Project documentation and guides (1 files)
- **`frontend/`** - project files

## Files

### `CLASS_SEEDING_REFACTOR_REPORT.md`
**Role:** documentation | **Lines:** 57

This Markdown file documents findings and suggestions for refactoring the class seeding logic in the `backend/seed/faradhaven_classes/` directory. It identifies redundant code, inconsistent level progression logic, and legacy text blobs used for storing class features. The report proposes specific actions, such as removing unused fields, consolidating level progression data, and relying on structured data instead of text blobs. This document serves as a guide for improving the clarity, maintainability, and robustness of the class seeding process.

---

### `CLAUDE.md`
**Role:** documentation | **Lines:** 93

This Markdown file provides instructions and context for the Claude Code AI assistant to effectively work with the project's codebase. It includes a project overview, common commands for running the backend and frontend, and a high-level architectural description. The file also points to key directories and technologies used in both the backend and frontend, enabling Claude to understand the project structure and assist with code-related tasks. This document facilitates AI-assisted development by providing essential project information.

---

### `CONFUSING_LOGIC_AND_UI_REPORT.md`
**Role:** documentation | **Lines:** 92

This Markdown file details confusing mechanics in the backend's class definitions and their unclear implementation in the frontend's character sheet. It focuses on specific classes like the Lorewright and Sanguinist, highlighting issues such as overly complex resource management and punitive notoriety systems. The report provides concrete suggestions for simplifying the backend logic and improving the frontend's UI to better represent these mechanics. This document aims to improve the player experience by addressing confusing game mechanics and enhancing their presentation in the user interface.

---

### `DEPRECATION_REPORT.md`
**Role:** documentation | **Lines:** 111

This Markdown file documents deprecated or dead code within the project, specifically focusing on the removal of the `TotalHP` field and the legacy class resource system. It describes the deprecated elements, their locations in the codebase, and the actions taken to remove them. The report also includes a class-by-class migration plan for ensuring that resources are correctly captured by the new system. This document serves as a record of code cleanup efforts and provides guidance for developers on avoiding deprecated features.

---

### `.gitignore`
**Role:** source file | **Lines:** 55

This file specifies intentionally untracked files that Git should ignore. It prevents sensitive or unnecessary files, such as environment variables, logs, build outputs, and IDE-specific files, from being committed to the repository. This helps keep the repository clean, reduces its size, and avoids accidental exposure of sensitive information. By excluding these files, the `.gitignore` file contributes to a more organized and secure development workflow.

## Stats

- Total files: 5
- Direct subfolders: 3
- Has tests: no
- Has config: no
