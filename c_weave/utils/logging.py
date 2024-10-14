import logging


def get_logger(name):
    return logging.getLogger(name)


def configure_logging(debug_level):
    log_levels = {0: logging.WARNING, 1: logging.INFO, 2: logging.DEBUG}

    logging.basicConfig(
        level=log_levels[debug_level],
        format="[%(asctime)s] %(levelname)s: %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    logging.getLogger("colormath").setLevel(logging.WARNING)
