"""
UrbanSense - ML Configuration Loader

Provides utilities to load and parse YAML training configuration files with
zero external dependencies fallback.
"""

from pathlib import Path
from typing import Dict, Any, Optional

DEFAULT_CONFIG_PATH = Path(__file__).parent / "train_config.yaml"


def parse_simple_yaml_config(yaml_path: Path) -> Dict[str, Any]:
    """
    Parses a simple key-value YAML configuration file without PyYAML dependency.
    Converts booleans, ints, floats, and strings automatically.
    """
    if not yaml_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {yaml_path}")

    config: Dict[str, Any] = {}
    lines = yaml_path.read_text(encoding="utf-8").splitlines()

    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        if ":" in line:
            key, val = line.split(":", 1)
            key = key.strip()
            val = val.strip()

            # Remove trailing comments
            if " #" in val:
                val = val.split(" #", 1)[0].strip()

            # Unquote string
            if (val.startswith("'") and val.endswith("'")) or (val.startswith('"') and val.endswith('"')):
                val = val[1:-1]

            # Convert types
            if val.lower() == "true":
                config[key] = True
            elif val.lower() == "false":
                config[key] = False
            elif val.lower() == "null" or val == "":
                config[key] = None
            else:
                try:
                    config[key] = int(val)
                except ValueError:
                    try:
                        config[key] = float(val)
                    except ValueError:
                        config[key] = val

    return config


def load_train_config(config_path: Optional[Path] = None) -> Dict[str, Any]:
    """
    Loads training parameters from the specified config YAML file, or defaults
    to ml/config/train_config.yaml.
    """
    target_path = config_path or DEFAULT_CONFIG_PATH
    try:
        import yaml
        with open(target_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except ImportError:
        return parse_simple_yaml_config(target_path)
