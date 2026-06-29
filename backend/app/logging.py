"""Logging setup for the FastAPI process."""

import logging


LOGGER_NAME = "legal-pipeline"


def configure_logging() -> logging.Logger:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    return logging.getLogger(LOGGER_NAME)

