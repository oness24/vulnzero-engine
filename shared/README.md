# Shared

Common code shared across all services.

## Structure

- **models/**: Pydantic models and SQLAlchemy ORM models
- **utils/**: Utility functions and helpers
- **config/**: Configuration management

## Usage

```python
from shared.models import Vulnerability, Asset
from shared.utils import logger
from shared.config import settings
```
