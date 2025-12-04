# Change log

## 0.0.2

### Significant Changes

- Implemented LoggingMixin across the entire codebase Logging is now configured via a flexible config file and applied consistently to services running under Gunicorn and Celery workers.
- PEP8 compliance enforced with flake8 Codebase has been standardized to follow PEP8 guidelines, improving readability and consistency.
- Exception handling added Structured exception management has been introduced throughout the application to ensure stability and meaningful error reporting.
- Centralized cookie configuration All cookie attributes (SameSite, Secure, HttpOnly, Max-Age) have been moved into configuration for easier environment‑specific adjustments.
- Optimized token truncation algorithm in LLM service Token handling has been refined to reduce overhead and improve response efficiency.
- Resource management for LLM service Monitoring and control mechanisms for CPU, memory, and GPU usage have been added to prevent resource exhaustion and improve throughput.
- Enhanced JWT security Strengthened JWT handling with improved signing algorithms, validation, and expiration policies.
- Safe type casting for parameters Input parameters are now strictly validated and safely cast to prevent runtime errors and injection risks.
- Adopted `asyncio.run` for async functions in synchronous contexts Ensures proper execution of asynchronous functions when invoked from synchronous environments.
- Refactored the entire codebase Major restructuring completed to reduce technical debt, improve modularity, and prepare the system for future scalability.

### Bug fixes
- Filter query results by message id

### Miscellaneous