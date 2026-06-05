from pathlib import Path
import logging

BASE_DIR = Path(__file__).resolve().parent.parent
LOG_FILE = BASE_DIR / "app.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] - %(name)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOG_FILE, mode="a")
    ]
)

logger = logging.getLogger("app")