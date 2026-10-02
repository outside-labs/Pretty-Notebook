"""Runtime configuration for the supported single-process web topology."""

from pathlib import Path

from decouple import config

WEB_ROOT = Path(__file__).resolve().parent
DEFAULT_SETTINGS_PATH = WEB_ROOT / "web-settings.json"


def data_root() -> Path:
    """Return the persistent state directory configured before process start."""
    configured = config("PNBP_DATA_DIR", default=str(WEB_ROOT / "data"))
    return Path(configured).expanduser().resolve()


DATA_ROOT = data_root()
PAGES_PATH = (DATA_ROOT / "pages").resolve()
IMAGES_PATH = (DATA_ROOT / "images").resolve()
SETTINGS_PATH = (DATA_ROOT / "web-settings.json").resolve()
DATABASE_URL = config(
    "PNBP_DATABASE_URL",
    default=f"sqlite://{(DATA_ROOT / 'db.sqlite3').resolve()}",
)


def allowed_hosts() -> list[str]:
    """Parse the explicit Host allowlist used by TrustedHostMiddleware."""
    raw = config(
        "PNBP_ALLOWED_HOSTS",
        default="127.0.0.1,localhost,testserver",
    )
    hosts = [host.strip() for host in raw.split(",") if host.strip()]
    if not hosts or "*" in hosts:
        raise RuntimeError("PNBP_ALLOWED_HOSTS must contain explicit host names")
    if any("://" in host or "/" in host or "\\" in host for host in hosts):
        raise RuntimeError("PNBP_ALLOWED_HOSTS contains an invalid host name")
    return hosts
