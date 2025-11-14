# Development Guide & Coding Patterns

This document provides a comprehensive guide for developers working on the Weather AI Agent project, including setup instructions, architecture overview, and coding patterns.

## Table of Contents

1. [Development Setup](#development-setup)
2. [Project Architecture](#project-architecture)
3. [Coding Patterns](#coding-patterns)
4. [Testing](#testing)
5. [Contributing](#contributing)

---

## Development Setup

### Prerequisites

- Python 3.9 or higher
- pip (Python package manager)
- Git
- A code editor (VS Code recommended)

### Local Environment Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/weather-agent.git
   cd weather-agent
   ```

2. **Create a virtual environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   
   Create a `.env` file in the project root:
   ```bash
   LOCATION_LAT=48.8566
   LOCATION_LON=2.3522
   NTFY_TOPIC=your_topic_name
   GROQ_API_KEY=your_groq_key
   # Optional:
   WEATHERAPI_KEY=your_weatherapi_key
   OPENWEATHER_KEY=your_openweather_key
   HUGGINGFACE_API_KEY=your_hf_key
   ```

5. **Run the agent locally**
   ```bash
   cd src
   python weather_agent.py
   ```

6. **Run tests**
   ```bash
   python test_agent.py
   ```

### IDE Setup (VS Code)

Recommended extensions:
- Python (Microsoft)
- Pylance (for type checking)
- Python Docstring Generator

Settings (`.vscode/settings.json`):
```json
{
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": false,
  "python.linting.flake8Enabled": true,
  "python.formatting.provider": "black",
  "python.testing.pytestEnabled": false,
  "python.testing.unittestEnabled": true
}
```

---

## Project Architecture

### Overview

The Weather AI Agent follows a modular architecture with clear separation of concerns:

```
┌─────────────────────────────────────────────────────────┐
│                    weather_agent.py                      │
│              (Main Orchestrator)                         │
└──────────────┬──────────────────────────────────────────┘
               │
       ┌───────┴────────┬──────────────┬──────────────┐
       │                │              │              │
┌──────▼──────┐  ┌──────▼──────┐  ┌───▼────────┐  ┌─▼──────────┐
│ Weather     │  │ AI          │  │ Reflection │  │ Utils      │
│ Sources     │  │ Recommender │  │ Engine     │  │ (DRY)      │
└─────────────┘  └─────────────┘  └────────────┘  └────────────┘
       │                │              │              │
       └────────────────┴──────────────┴──────────────┘
                        │
              ┌─────────▼─────────┐
              │  External APIs    │
              │  (Weather, AI)    │
              └───────────────────┘
```

### Core Modules

#### 1. `weather_agent.py` - Main Orchestrator
- Coordinates the entire workflow
- Manages environment configuration
- Handles error reporting
- Integrates reflection engine

#### 2. `weather_sources.py` - Data Aggregation
- Fetches from multiple weather APIs
- Aggregates data using statistical methods
- Handles source failures gracefully
- Calculates reliability scores

#### 3. `ai_recommender.py` - AI Recommendations
- Generates clothing recommendations using AI
- Supports multiple AI providers (Groq, Hugging Face)
- Implements iterative refinement with reflection
- Formats notifications

#### 4. `reflection_engine.py` - Self-Evaluation
- Evaluates output quality
- Identifies issues and suggests improvements
- Enables iterative refinement
- Provides quality scoring

#### 5. `utils.py` - Shared Utilities
- Common functions following DRY principles
- API fetching helpers
- Validation functions
- Formatting utilities

---

## Coding Patterns

### 1. DRY (Don't Repeat Yourself) Principle

The codebase extensively applies DRY principles to eliminate duplication.

#### Utility Functions (`src/utils.py`)

**Common API Fetching:**
```python
# Before: Repeated try-except blocks in each fetch method
# After: Single reusable function
data = fetch_api_data(
    url="https://api.example.com",
    params={'key': 'value'},
    timeout=10,
    source_name="Example API"
)
```

**Safe Type Conversion:**
```python
# Before: Repeated try-except for float conversion
# After: Single utility function
temp = safe_float(hour_data.get('temperature'), default=0.0)
```

**Unit Conversions:**
```python
# Before: Repeated conversion logic
wind_speed = hour['wind_kph'] / 3.6  # Scattered throughout code

# After: Centralized conversion
wind_speed = kmh_to_ms(hour['wind_kph'])
```

**Validation:**
```python
# Before: Repeated validation logic
# After: Reusable validation functions
lat, lon = validate_coordinates(lat_str, lon_str)
env_vars = validate_required_env_vars(['LOCATION_LAT', 'LOCATION_LON'])
```

#### Generic Data Processing

**Hourly Data Processing:**
```python
# Generic function to process hourly data from any source
def _process_hourly_data(
    self,
    data_items: List,
    extractor: Callable[[any], Dict],
    max_items: int = 10,
    filter_func: Optional[Callable] = None
) -> List[Dict]:
    """Generic function to process hourly data from any source."""
    # Used by all fetch methods, eliminating duplication
```

**Benefits:**
- Single source of truth for common operations
- Easier maintenance (fix once, works everywhere)
- Consistent error handling
- Reduced code size (~30% reduction in weather_sources.py)

### 2. Reflection Pattern

The agent implements a self-evaluation pattern where it critically assesses its own outputs.

#### How It Works

```python
# 1. Generate initial output
recommendation = ai_recommender.generate_recommendation(weather_data)

# 2. Reflect on quality
reflection = reflection_engine.reflect_on_recommendation(
    recommendation, weather_data
)

# 3. Refine if needed
if not reflection.passed:
    refined = ai_recommender._generate_with_feedback(
        weather_data,
        reflection.issues,
        reflection.suggestions
    )
```

#### Implementation Points

**Weather Data Reflection:**
- Checks data completeness
- Validates source diversity
- Assesses reliability scores
- Identifies consistency issues

**Recommendation Reflection:**
- Validates length and relevance
- Checks for actionable advice
- Verifies consistency with weather
- Iterative refinement (up to 2 iterations)

**Notification Reflection:**
- Validates completeness
- Checks required sections
- Ensures proper formatting

See [REFLECTION_PATTERN.md](REFLECTION_PATTERN.md) for detailed documentation.

### 3. Strategy Pattern

The codebase uses strategy pattern for interchangeable components.

#### AI Provider Strategy

```python
class AIRecommender:
    def generate_recommendation(self, weather_data: Dict) -> str:
        if self.groq_api_key:
            return self._generate_with_groq(weather_data)
        elif self.hf_api_key:
            return self._generate_with_huggingface(weather_data)
```

**Benefits:**
- Easy to add new AI providers
- Clean separation of concerns
- Consistent interface across providers

#### Weather Source Strategy

Multiple weather sources can be added/removed without changing core logic:

```python
sources = {
    'Open-Meteo': self.fetch_open_meteo(),
    'WeatherAPI': self.fetch_weatherapi(),
    'OpenWeatherMap': self.fetch_openweathermap(),
    # Easy to add more sources
}
```

### 4. Error Handling Pattern

Consistent error handling across the codebase:

```python
# Centralized error handling in utils
def fetch_api_data(...) -> Optional[Dict]:
    try:
        response = requests.get(url, ...)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"{source_name} error: {e}")
        return None  # Graceful degradation
```

**Principles:**
- Fail gracefully (return None, not crash)
- Log errors with context
- Continue with available data
- User-friendly error messages

### 5. Configuration Pattern

Environment-based configuration with validation:

```python
# Load and validate configuration
load_env_file()
env_vars = validate_required_env_vars(['LOCATION_LAT', 'LOCATION_LON'])
lat, lon = validate_coordinates(env_vars['LOCATION_LAT'], env_vars['LOCATION_LON'])
```

**Benefits:**
- Type-safe configuration
- Early validation
- Clear error messages
- Supports both .env files and environment variables

### 6. Separation of Concerns

Each module has a single, well-defined responsibility:

- **weather_sources.py**: Only handles data fetching and aggregation
- **ai_recommender.py**: Only handles AI interactions and formatting
- **reflection_engine.py**: Only handles quality evaluation
- **utils.py**: Only provides shared utilities
- **weather_agent.py**: Only orchestrates the workflow

### 7. Type Hints

Extensive use of type hints for better code clarity and IDE support:

```python
def fetch_api_data(
    url: str,
    params: Optional[Dict] = None,
    headers: Optional[Dict] = None,
    method: str = 'GET',
    timeout: int = 10,
    source_name: str = "API"
) -> Optional[Dict]:
    """Generic function to fetch data from an API."""
```

### 8. Consistent Formatting

Standardized message formatting:

```python
# Utility functions for consistent output
print_success("Operation completed", indent=3)
print_error("Operation failed", indent=3)
print_warning("Potential issue", indent=3)
```

---

## Testing

### Running Tests

```bash
# Run all tests
python test_agent.py

# Test specific components
python -m pytest tests/  # If pytest is set up
```

### Test Coverage

The `test_agent.py` script tests:
- Module imports
- Environment variable validation
- Coordinate validation
- Weather source connectivity
- Ntfy.sh connectivity

### Writing Tests

When adding new features:

1. **Test the happy path**: Normal operation
2. **Test error cases**: Missing data, API failures
3. **Test edge cases**: Boundary conditions
4. **Test integration**: Multiple components working together

Example:
```python
def test_weather_aggregation():
    """Test weather data aggregation with multiple sources."""
    weather = WeatherSources(lat=48.8566, lon=2.3522)
    data = weather.aggregate_weather_data()
    
    assert len(data.sources_used) >= 2
    assert len(data.hourly_data) > 0
    assert 0.0 <= data.reliability_score <= 1.0
```

---

## Contributing

### Code Style Guidelines

1. **Follow PEP 8**: Python style guide
2. **Use type hints**: For function parameters and returns
3. **Write docstrings**: For all public functions and classes
4. **Keep functions small**: Single responsibility principle
5. **Use meaningful names**: Variables and functions should be self-documenting

### Pull Request Process

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/your-feature`
3. **Make your changes**: Following coding patterns
4. **Test your changes**: Run `test_agent.py`
5. **Update documentation**: If adding features
6. **Submit PR**: With clear description

### Commit Messages

Use clear, descriptive commit messages:

```
feat: Add new weather source integration
fix: Resolve coordinate validation edge case
refactor: Extract common API fetching logic
docs: Update development guide
```

### Areas for Contribution

- **New weather sources**: Add more APIs
- **AI improvements**: Better prompts, new models
- **Reflection enhancements**: Better quality metrics
- **Testing**: More comprehensive test coverage
- **Documentation**: Improve guides and examples
- **Performance**: Optimize API calls, caching

---

## Architecture Decisions

### Why Multiple Weather Sources?

- **Reliability**: If one source fails, others continue
- **Accuracy**: Aggregating multiple sources improves accuracy
- **Consistency**: Outlier detection and removal

### Why Reflection Pattern?

- **Quality Assurance**: Ensures outputs meet standards
- **Self-Correction**: Agent improves its own work
- **Transparency**: Users see quality assessments

### Why DRY Principles?

- **Maintainability**: Fix bugs in one place
- **Consistency**: Same logic everywhere
- **Reduced Complexity**: Less code to understand

### Why Utility Module?

- **Reusability**: Common functions available everywhere
- **Testability**: Easy to test utilities independently
- **Organization**: Clear separation of concerns

---

## Common Tasks

### Adding a New Weather Source

1. Add fetch method to `WeatherSources` class:
```python
def fetch_new_source(self) -> Optional[List[Dict]]:
    data = fetch_api_data(
        url="https://api.new-source.com",
        params={'lat': self.lat, 'lon': self.lon},
        timeout=self.timeout,
        source_name="New Source"
    )
    if not data:
        return None
    
    return self._process_hourly_data(
        data['forecast'],
        lambda item: {
            'time': item['time'],
            'temperature': item['temp'],
            # ... map fields
        },
        max_items=10
    )
```

2. Add to aggregation:
```python
sources = {
    # ... existing sources
    'New Source': self.fetch_new_source(),
}
```

3. Add weight in `source_weights` dict

### Adding a New AI Provider

1. Add generation method:
```python
def _generate_with_new_provider(self, weather_data: Dict) -> str:
    # Implementation
```

2. Update `generate_recommendation()`:
```python
if self.new_provider_key:
    return self._generate_with_new_provider(weather_data)
```

### Modifying Reflection Criteria

Edit `reflection_engine.py`:

```python
def reflect_on_recommendation(self, recommendation: str, weather_data: Dict):
    # Add new checks
    if new_condition:
        issues.append("New issue")
        scores.append(0.5)
    # ...
```

---

## Resources

- [Python Type Hints](https://docs.python.org/3/library/typing.html)
- [PEP 8 Style Guide](https://pep8.org/)
- [DRY Principle](https://en.wikipedia.org/wiki/Don%27t_repeat_yourself)
- [Reflection Pattern](REFLECTION_PATTERN.md)

---

## Questions?

- Open an issue on GitHub
- Check existing documentation
- Review code comments
- See [REFLECTION_PATTERN.md](REFLECTION_PATTERN.md) for reflection details

