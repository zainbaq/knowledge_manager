"""Centralized rate limiter instance shared across API modules."""

from slowapi import Limiter
from slowapi.util import get_remote_address

from config import DEFAULT_RATE_LIMIT

limiter = Limiter(key_func=get_remote_address, default_limits=[DEFAULT_RATE_LIMIT])
