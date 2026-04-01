# Load Tempo integration so COIN_SYMBOL_MAPPINGS is patched before any app code runs.
from . import tempo  # noqa: F401
