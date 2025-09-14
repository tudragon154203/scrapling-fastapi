# Project Brief

## Overview
Scrapling FastAPI Service is a web scraping API built with FastAPI that provides a clean interface for crawling websites using Camoufox (a stealthy browser automation tool). The service supports proxy rotation, retry logic, and various stealth features to avoid detection.

## Goals
- Provide a reliable web scraping API with stealth capabilities
- Support persistent user data for session management
- Implement proxy rotation and health checking
- Enable various stealth options for bot detection avoidance
- Maintain clean, testable, and maintainable code

## Key Features
- Generic crawl endpoint with flexible options
- Proxy support (private and public proxy lists)
- Retry logic with exponential backoff
- User data persistence via Camoufox
- Stealth options (geoip spoofing, window sizing, locale settings)
- Health monitoring for proxies

## Technology Stack
- Python 3.10+
- FastAPI for API framework
- Camoufox/Scrapling for browser automation
- Pydantic for data validation
- Comprehensive test suite with python -m pytest