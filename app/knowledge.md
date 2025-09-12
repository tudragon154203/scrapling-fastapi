# App Directory Knowledge

## Directory Structure

### API Layer (`api/`)
- **routes.py**: Main router aggregating all endpoint routers
- **health.py**: Simple `/health` readiness endpoint
- **crawl.py**: Generic crawling endpoints (`/crawl`, `/crawl/dpd`, `/crawl/auspost`)
- **browse.py**: Interactive browsing endpoint (`/browse`)
- **tiktok.py**: TikTok-specific endpoints (`/tiktok/session`, `/tiktok/search`)

### Core Layer (`core/`)
- **config.py**: Application settings with environment variable loading
- **logging.py**: Centralized logging setup and configuration

### Services Layer (`services/`)

#### Common Services (`services/common/`)
- **engine.py**: `CrawlerEngine` - main orchestration component
- **interfaces.py**: Abstract interfaces for crawler components
- **types.py**: Type definitions and data structures
- **executor.py**: Base executor interfaces and implementations
- **adapters/scrapling_fetcher.py**: Bridge to Scrapling library
- **browser/camoufox.py**: Camoufox argument building and configuration
- **browser/user_data.py**: User data directory management and cloning

#### Crawler Services (`services/crawler/`)
- **generic.py**: `GenericCrawler` for basic web crawling
- **dpd.py**: `DPDCrawler` for DPD tracking pages
- **auspost.py**: `AuspostCrawler` with humanization features
- **executors/**: Execution strategies (single, retry, backoff)
- **proxy/**: Proxy management (health, rotation, sources)
- **actions/**: Custom page actions for specific sites

#### Browser Services (`services/browser/`)
- **browse.py**: `BrowseCrawler` for interactive sessions
- **executors/browse_executor.py**: Browser session execution logic
- **actions/**: Browser-specific actions (humanize, scroll, wait)
- **options/resolver.py**: Option resolution and validation

#### TikTok Services (`services/tiktok/`)
- **service.py**: `TiktokService` for session and search operations
- **tiktok_executor.py**: TikTok-specific execution logic
- **parser.py**: TikTok page parsing and data extraction
- **utils/login_detection.py**: Login status detection methods

### Schemas Layer (`schemas/`)
- **crawl.py**: `CrawlRequest`/`CrawlResponse` for generic crawling
- **browse.py**: `BrowseRequest`/`BrowseResponse` for interactive sessions
- **tiktok.py**: TikTok-specific request/response models
- **dpd.py**: DPD tracking request/response models
- **auspost.py**: AusPost tracking request/response models

## Key Patterns

### Service Factory Pattern
```python
# Services use factory methods for configuration
engine = CrawlerEngine.from_settings()
crawler = GenericCrawler(engine)
```

### Dependency Injection
```python
# Components accept optional dependencies for testing
class CrawlerEngine:
    def __init__(self, executor=None, fetch_client=None, ...):
        self.executor = executor or default_executor
```

### Interface Segregation
```python
# Clean interfaces for different concerns
class ICrawlerEngine:
    def run(self, request, page_action=None) -> CrawlResponse:
        pass

class IExecutor:
    def execute(self, request, page_action=None) -> CrawlResponse:
        pass
```

### Configuration Composition
```python
# Settings compose from environment with type safety
class Settings(BaseSettings):
    camoufox_user_data_dir: Optional[str] = None
    model_config = SettingsConfigDict(env_file=".env")
```

## Component Relationships

### Request Flow
1. **API Router** receives HTTP request
2. **Schema** validates and parses request body
3. **Crawler Service** (Generic/DPD/AusPost/TikTok) processes request
4. **CrawlerEngine** orchestrates execution
5. **Executor** (Single/Retry) handles actual crawling
6. **ScraplingFetcherAdapter** interfaces with browser automation
7. **Response Schema** structures the return data

### Configuration Flow
1. **Environment variables** loaded by `config.py`
2. **Settings object** cached and shared across services
3. **Components** access settings for initialization
4. **Runtime options** merged with defaults

### Error Propagation
1. **Low-level errors** caught by executors
2. **Retry logic** applied based on error type
3. **Meaningful errors** propagated to API layer
4. **HTTP status codes** mapped appropriately

## Testing Integration Points

### Mockable Components
- `ScraplingFetcherAdapter` - mock browser automation
- `CrawlerEngine` - mock entire crawling pipeline
- Individual crawlers - mock specific service behavior

### Configuration Override
- Test fixtures can override settings
- Environment variables for test configuration
- Capability detection can be mocked

### Isolation Strategies
- Unit tests mock external dependencies
- Integration tests use real browser automation
- Contract tests validate API schemas