import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


def configure_logging(app):
    """
    Grava logs em logs/app.log (rotaciona em 1 MB, guarda 5
    arquivos antigos). Nunca registrar senhas ou tokens.
    """

    log_dir = Path(app.root_path) / "logs"

    log_dir.mkdir(exist_ok=True)

    handler = RotatingFileHandler(
        log_dir / "app.log",
        maxBytes=1_000_000,
        backupCount=5,
        encoding="utf-8"
    )

    handler.setLevel(logging.INFO)

    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s %(levelname)s %(message)s"
        )
    )

    app.logger.addHandler(handler)

    app.logger.setLevel(logging.INFO)
