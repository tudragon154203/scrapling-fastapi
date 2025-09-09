import logging
from typing import Any, Optional

import app.core.config as app_config
from app.schemas.crawl import CrawlRequest, CrawlResponse
from app.services.common.interfaces import ICrawlerEngine, IExecutor, PageAction
from app.services.common.adapters.scrapling_fetcher import ScraplingFetcherAdapter
from app.services.browser.options.resolver import OptionsResolver
from app.services.common.browser.camoufox import CamoufoxArgsBuilder
from app.services.crawler.executors.single_executor import SingleAttemptExecutor
from app.services.crawler.executors.retry_executor import RetryingExecutor
from app.services.crawler.executors.backoff import BackoffPolicy
from app.services.crawler.proxy.plan import AttemptPlanner
from app.services.crawler.proxy.health import get_health_tracker

logger = logging.getLogger(__name__)


class CrawlerEngine(ICrawlerEngine):
    """Main crawler engine that orchestrates crawl operations using OOP components."""
    
    def __init__(self, 
                 executor: Optional[IExecutor] = None,
                 fetch_client: Optional[ScraplingFetcherAdapter] = None,
                 options_resolver: Optional[OptionsResolver] = None,
                 camoufox_builder: Optional[CamoufoxArgsBuilder] = None,
                 backoff_policy: Optional[BackoffPolicy] = None,
                 attempt_planner: Optional[AttemptPlanner] = None,
                 health_tracker: Optional[Any] = None):
        self.executor = executor
        self.fetch_client = fetch_client or ScraplingFetcherAdapter()
        self.options_resolver = options_resolver or OptionsResolver()
        self.camoufox_builder = camoufox_builder or CamoufoxArgsBuilder()
        self.backoff_policy = backoff_policy
        self.attempt_planner = attempt_planner or AttemptPlanner()
        self.health_tracker = health_tracker
    
    @classmethod
    def from_settings(cls, settings=None) -> 'CrawlerEngine':
        """Factory method to create engine with default components from settings."""
        if settings is None:
            import app.core.config as app_config
            settings = app_config.get_settings()
        
        # Decide executor strategy based on max_retries
        if settings.max_retries <= 1:
            executor = SingleAttemptExecutor()
        else:
            backoff_policy = BackoffPolicy.from_settings(settings)
            retry_executor = RetryingExecutor(
                backoff_policy=backoff_policy,
                health_tracker=get_health_tracker()
            )
            executor = retry_executor
        
        # Create other default components
        fetch_client = ScraplingFetcherAdapter()
        options_resolver = OptionsResolver()
        camoufox_builder = CamoufoxArgsBuilder()
        
        return cls(
            executor=executor,
            fetch_client=fetch_client,
            options_resolver=options_resolver,
            camoufox_builder=camoufox_builder
        )
    
    def run(self, request: CrawlRequest, page_action: Optional[PageAction] = None) -> CrawlResponse:
        """Run a crawl request with optional page action."""
        if self.executor is None:
            # Lazily create executor based on settings
            settings = app_config.get_settings()
            self.executor = self._create_executor(settings)
        
        return self.executor.execute(request, page_action)
    
    def _create_executor(self, settings) -> IExecutor:
        """Create appropriate executor based on settings."""
        if settings.max_retries <= 1:
            return SingleAttemptExecutor(
                fetch_client=self.fetch_client,
                options_resolver=self.options_resolver,
                camoufox_builder=self.camoufox_builder
            )
        else:
            backoff_policy = BackoffPolicy.from_settings(settings)
            return RetryingExecutor(
                fetch_client=self.fetch_client,
                options_resolver=self.options_resolver,
                camoufox_builder=self.camoufox_builder,
                backoff_policy=backoff_policy,
                attempt_planner=self.attempt_planner,
                health_tracker=self.health_tracker or get_health_tracker()
            )
