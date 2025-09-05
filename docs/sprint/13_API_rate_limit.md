Global rate limit:

+ all /crawl/* endpoints: 15 req/minute for load balancing
+ /health endpoints: 60 req/minute
+ concurrency /crawl/*: 4 req/container-uvicorn
+ per (IP, base_url): 4 req/minute/(IP, base_url) to avoid spamming

Lib to use: fastapi-limiter
