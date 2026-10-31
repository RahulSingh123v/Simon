
import logging
import time

from simon.core.config import load_settings
from simon.core.logging_config import configure_logging


def main() -> None:
    settings = load_settings()
    configure_logging(settings)

    logger = logging.getLogger("simon")
    logger.info("SIMON initialization started")

    print(f"{settings.app_name} is initializing...")
    time.sleep(1)

    print("The environment has been successfully initialized.")
    print(f"Database: {settings.database_path}")
    print(f"Model endpoint: {settings.model_base_url}")

    logger.info("SIMON initialization completed")
    print("SIMON is ready.")


if __name__ == "__main__":
    main()
