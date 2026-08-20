from app.core.config import get_settings
from app.core.logging import setup_logging

setup_logging(get_settings().debug)
