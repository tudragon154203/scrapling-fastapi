# Constitution Amendment Summary

## Version Change
- **From**: 1.4.0
- **To**: 1.4.1
- **Type**: PATCH (Clarification/Documentation update)

## Changes Made

### 1. Constitution Document (.specify/memory/constitution.md)
- Updated Principle VI "Spec-Driven Code Location" to reflect the new path structure
- Changed from: "Spec-related code, including the main source code folder (`.specify/src/`), MUST be located within the `.specify/` directory."
- Changed to: "Spec-related code, including the main source code folder (`specify_src/`), MUST be located within the project root directory."
- Updated Sync Impact Report to document the change

### 2. Template Updates
- **plan-template.md**: Updated the project structure example to use `specify_src/` instead of `.specify/src/`
- **tasks-template.md**: Updated path conventions and task examples to use `specify_src/`
- **QWEN.md**: Updated project structure documentation to reflect the new path

### 3. Feature Specification Updates
- **specs/001-change-tiktok-search/plan.md**: Updated project structure example
- **specs/001-change-tiktok-search/tasks.md**: Updated path conventions and task examples

### 4. Script Updates
- **.specify/scripts/powershell/update-agent-context.ps1**: Updated project structure generation to use `specify_src/`

## Rationale
This is a PATCH version update because it's a clarification/documentation change that doesn't affect the core principles or add/remove functionality. It simply updates the documentation to reflect the actual project structure that has already been implemented.

## Files Requiring Manual Follow-up
None. All templates and documentation have been updated to reflect the new path structure.