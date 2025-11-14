"""
Utility functions for common operations across the codebase.
Applies DRY principles by centralizing repeated logic.
"""

import os
import sys
import requests
from typing import Dict, Optional, Any, Callable, Tuple
from functools import wraps


def load_env_file():
    """Load .env file if python-dotenv is available."""
    try:
        from dotenv import load_dotenv
        # Load .env file from parent directory (project root)
        env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
        if os.path.exists(env_path):
            load_dotenv(env_path)
        # Also try loading from current directory
        load_dotenv()
    except ImportError:
        pass  # python-dotenv not installed, skip .env loading


def safe_float(value: Any, default: float = 0.0) -> float:
    """Safely convert a value to float, returning default on failure."""
    if value is None:
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def kmh_to_ms(speed_kmh: float) -> float:
    """Convert speed from km/h to m/s."""
    return speed_kmh / 3.6


def validate_coordinates(lat: Any, lon: Any) -> Tuple[float, float]:
    """
    Validate and convert coordinates to floats.
    Raises ValueError if coordinates are invalid.
    """
    try:
        lat_float = float(lat)
        lon_float = float(lon)
    except (ValueError, TypeError):
        raise ValueError("LOCATION_LAT and LOCATION_LON must be valid numbers")
    
    if not (-90 <= lat_float <= 90 and -180 <= lon_float <= 180):
        raise ValueError("Coordinates out of valid range (lat: -90 to 90, lon: -180 to 180)")
    
    return lat_float, lon_float


def validate_required_env_vars(required_vars: list) -> Dict[str, str]:
    """
    Validate that required environment variables are set.
    Returns dict of variable names to values.
    Raises SystemExit if any are missing.
    """
    missing = []
    values = {}
    
    for var in required_vars:
        value = os.getenv(var)
        if not value:
            missing.append(var)
        else:
            values[var] = value
    
    if missing:
        print(f"❌ ERROR: Required environment variables not set: {', '.join(missing)}")
        sys.exit(1)
    
    return values


def fetch_api_data(
    url: str,
    params: Optional[Dict] = None,
    headers: Optional[Dict] = None,
    method: str = 'GET',
    timeout: int = 10,
    source_name: str = "API",
    json_data: Optional[Dict] = None
) -> Optional[Dict]:
    """
    Generic function to fetch data from an API with consistent error handling.
    Returns JSON response as dict, or None on error.
    """
    try:
        if method.upper() == 'GET':
            response = requests.get(url, params=params, headers=headers, timeout=timeout)
        elif method.upper() == 'POST':
            response = requests.post(url, params=params, headers=headers, json=json_data, timeout=timeout)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")
        
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"{source_name} error: {e}")
        return None


def handle_step_execution(step_name: str, step_number: int = None):
    """
    Decorator for handling step execution with consistent error handling.
    Prints step header and handles exceptions uniformly.
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            if step_number:
                print(f"\n{step_name} Step {step_number}: {func.__name__.replace('_', ' ').title()}...")
            else:
                print(f"\n{step_name} {func.__name__.replace('_', ' ').title()}...")
            
            try:
                result = func(*args, **kwargs)
                print(f"✅ {step_name} completed successfully")
                return result
            except Exception as e:
                print(f"❌ Failed {step_name.lower()}: {e}")
                raise
        return wrapper
    return decorator


def print_success(message: str, indent: int = 0):
    """Print a success message with consistent formatting."""
    indent_str = " " * indent
    print(f"{indent_str}✅ {message}")


def print_error(message: str, indent: int = 0):
    """Print an error message with consistent formatting."""
    indent_str = " " * indent
    print(f"{indent_str}❌ {message}")


def print_warning(message: str, indent: int = 0):
    """Print a warning message with consistent formatting."""
    indent_str = " " * indent
    print(f"{indent_str}⚠️  {message}")


def extract_weather_fields(
    data: Dict,
    field_mapping: Dict[str, str],
    converters: Optional[Dict[str, Callable]] = None
) -> Dict[str, Any]:
    """
    Extract weather fields from API response using a field mapping.
    
    Args:
        data: API response dictionary
        field_mapping: Dict mapping output field names to nested keys (e.g., {'temperature': 'main.temp'})
        converters: Optional dict of field names to conversion functions
    
    Returns:
        Dict with extracted and converted values
    """
    result = {}
    converters = converters or {}
    
    for output_field, source_path in field_mapping.items():
        # Navigate nested dictionary using dot notation
        value = data
        for key in source_path.split('.'):
            if isinstance(value, dict):
                value = value.get(key)
            elif isinstance(value, list) and key.isdigit():
                value = value[int(key)] if int(key) < len(value) else None
            else:
                value = None
                break
        
        # Apply converter if provided
        if output_field in converters:
            value = converters[output_field](value)
        elif value is not None:
            # Default: try to convert to float if numeric
            try:
                value = float(value)
            except (ValueError, TypeError):
                pass
        
        result[output_field] = value
    
    return result

