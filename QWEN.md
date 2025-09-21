# Qwen Code Context

This file contains context information for Qwen Code about the current project.

## Recent Changes
1. Added headless/headful mode control to TikTok search functionality
2. Implemented optional force_headful parameter
3. Maintained test environment override to always use headless mode

## Tech Stack
- Python 3.11
- FastAPI
- Scrapling (browser automation)
- pytest (testing)

## Project Structure
- Single project structure with src/ and tests/ directories
- Feature specifications in specs/ directory
- Implementation follows test-first approach

## Key Entities
- SearchRequest: Request object with optional force_headful parameter
- ExecutionContext: Context determining if running in test environment
- BrowserMode: Enumeration for headless/headful modes

## API Contracts
- TikTok search endpoint accepts optional force_headful boolean parameter
- Returns execution_mode in response to indicate which mode was used
- Provides standard FastAPI validation errors for invalid parameters