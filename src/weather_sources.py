"""
Weather data fetching from multiple free sources.
Aggregates data from 5 different weather APIs for reliability.
"""

import requests
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import json
import math


class WeatherData:
    """Container for aggregated weather data."""
    
    def __init__(self):
        self.hourly_data = []  # List of hourly forecasts
        self.sources_used = []
        self.reliability_score = 0.0
        self.source_consistency_scores = {}  # Track how consistent each source is
    
    def to_dict(self):
        return {
            'hourly_data': self.hourly_data,
            'sources_used': self.sources_used,
            'reliability_score': self.reliability_score,
            'source_consistency_scores': self.source_consistency_scores
        }


class WeatherSources:
    """Fetch and aggregate weather data from multiple free sources."""
    
    def __init__(self, lat: float, lon: float, weatherapi_key: Optional[str] = None, 
                 openweather_key: Optional[str] = None):
        self.lat = lat
        self.lon = lon
        self.weatherapi_key = weatherapi_key
        self.openweather_key = openweather_key
        self.timeout = 10
        
        # Source reliability weights (based on typical API quality)
        # Higher weight = more reliable source
        self.source_weights = {
            'Open-Meteo': 1.0,      # High quality, free, no key needed
            'WeatherAPI': 1.2,       # Commercial API, generally accurate
            'OpenWeatherMap': 1.1,   # Well-established, reliable
            '7Timer': 0.8,           # Free but less detailed
            'wttr.in': 0.9           # Good coverage, free
        }
    
    def fetch_open_meteo(self) -> Optional[List[Dict]]:
        """Fetch from Open-Meteo (no API key needed)."""
        try:
            url = "https://api.open-meteo.com/v1/forecast"
            params = {
                'latitude': self.lat,
                'longitude': self.lon,
                'hourly': 'temperature_2m,precipitation,windspeed_10m,relativehumidity_2m,weathercode',
                'forecast_days': 1,
                'timezone': 'auto'
            }
            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            
            hourly_data = []
            current_hour = datetime.now().hour
            
            for i in range(current_hour, min(current_hour + 10, len(data['hourly']['time']))):
                hourly_data.append({
                    'time': data['hourly']['time'][i],
                    'temperature': data['hourly']['temperature_2m'][i],
                    'precipitation': data['hourly']['precipitation'][i],
                    'wind_speed': data['hourly']['windspeed_10m'][i],
                    'humidity': data['hourly']['relativehumidity_2m'][i],
                    'condition': self._decode_wmo_code(data['hourly']['weathercode'][i])
                })
            
            return hourly_data[:10]
        except Exception as e:
            print(f"Open-Meteo error: {e}")
            return None
    
    def fetch_weatherapi(self) -> Optional[List[Dict]]:
        """Fetch from WeatherAPI.com (free tier)."""
        if not self.weatherapi_key:
            return None
        
        try:
            url = "http://api.weatherapi.com/v1/forecast.json"
            params = {
                'key': self.weatherapi_key,
                'q': f"{self.lat},{self.lon}",
                'hours': 24,
                'aqi': 'no'
            }
            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            
            hourly_data = []
            current_time = datetime.now()
            
            for hour in data['forecast']['forecastday'][0]['hour']:
                hour_time = datetime.strptime(hour['time'], '%Y-%m-%d %H:%M')
                if hour_time >= current_time and len(hourly_data) < 10:
                    hourly_data.append({
                        'time': hour['time'],
                        'temperature': hour['temp_c'],
                        'precipitation': hour['precip_mm'],
                        'wind_speed': hour['wind_kph'] / 3.6,  # Convert to m/s
                        'humidity': hour['humidity'],
                        'condition': hour['condition']['text']
                    })
            
            return hourly_data
        except Exception as e:
            print(f"WeatherAPI error: {e}")
            return None
    
    def fetch_openweathermap(self) -> Optional[List[Dict]]:
        """Fetch from OpenWeatherMap (free tier)."""
        if not self.openweather_key:
            return None
        
        try:
            url = "https://api.openweathermap.org/data/2.5/forecast"
            params = {
                'lat': self.lat,
                'lon': self.lon,
                'appid': self.openweather_key,
                'units': 'metric',
                'cnt': 10
            }
            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            
            hourly_data = []
            for item in data['list'][:10]:
                hourly_data.append({
                    'time': item['dt_txt'],
                    'temperature': item['main']['temp'],
                    'precipitation': item.get('rain', {}).get('3h', 0) / 3,  # Convert 3h to 1h avg
                    'wind_speed': item['wind']['speed'],
                    'humidity': item['main']['humidity'],
                    'condition': item['weather'][0]['description']
                })
            
            return hourly_data
        except Exception as e:
            print(f"OpenWeatherMap error: {e}")
            return None
    
    def fetch_7timer(self) -> Optional[List[Dict]]:
        """Fetch from 7Timer (no API key needed)."""
        try:
            url = "http://www.7timer.info/bin/api.pl"
            params = {
                'lon': self.lon,
                'lat': self.lat,
                'product': 'civil',
                'output': 'json'
            }
            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            
            hourly_data = []
            for item in data['dataseries'][:10]:
                hourly_data.append({
                    'time': str(item['timepoint']),
                    'temperature': item['temp2m'],
                    'precipitation': self._estimate_precip_from_weather(item['weather']),
                    'wind_speed': item['wind10m']['speed'] * 0.277778,  # km/h to m/s
                    'humidity': item.get('rh2m', 50),
                    'condition': item['weather']
                })
            
            return hourly_data
        except Exception as e:
            print(f"7Timer error: {e}")
            return None
    
    def fetch_wttr(self) -> Optional[List[Dict]]:
        """Fetch from wttr.in (no API key needed)."""
        try:
            url = f"https://wttr.in/{self.lat},{self.lon}"
            params = {'format': 'j1'}
            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            
            hourly_data = []
            for hour in data['weather'][0]['hourly'][:10]:
                hourly_data.append({
                    'time': hour['time'],
                    'temperature': float(hour['tempC']),
                    'precipitation': float(hour['precipMM']),
                    'wind_speed': float(hour['windspeedKmph']) / 3.6,  # Convert to m/s
                    'humidity': float(hour['humidity']),
                    'condition': hour['weatherDesc'][0]['value']
                })
            
            return hourly_data
        except Exception as e:
            print(f"wttr.in error: {e}")
            return None
    
    def _remove_outliers(self, values: List[float], method: str = 'iqr') -> List[float]:
        """Remove outliers from a list of values using IQR method."""
        if len(values) < 3:
            return values
        
        sorted_vals = sorted(values)
        q1 = statistics.median(sorted_vals[:len(sorted_vals)//2])
        q3 = statistics.median(sorted_vals[len(sorted_vals)//2:])
        iqr = q3 - q1
        
        if iqr == 0:
            return values  # No spread, return all values
        
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr
        
        return [v for v in values if lower_bound <= v <= upper_bound]
    
    def _trimmed_mean(self, values: List[float], trim_percent: float = 0.1) -> float:
        """Calculate trimmed mean (removes extreme values)."""
        if len(values) < 3:
            return statistics.mean(values) if values else 0.0
        
        sorted_vals = sorted(values)
        trim_count = max(1, int(len(sorted_vals) * trim_percent))
        trimmed = sorted_vals[trim_count:-trim_count] if trim_count > 0 else sorted_vals
        
        return statistics.mean(trimmed) if trimmed else statistics.mean(values)
    
    def _weighted_median(self, values: List[float], weights: List[float]) -> float:
        """Calculate weighted median."""
        if not values or not weights or len(values) != len(weights):
            return statistics.median(values) if values else 0.0
        
        # Normalize weights
        total_weight = sum(weights)
        if total_weight == 0:
            return statistics.median(values)
        
        normalized_weights = [w / total_weight for w in weights]
        
        # Create pairs and sort by value
        pairs = list(zip(values, normalized_weights))
        pairs.sort(key=lambda x: x[0])
        
        # Find median position
        cumulative = 0.0
        for value, weight in pairs:
            cumulative += weight
            if cumulative >= 0.5:
                return value
        
        return pairs[-1][0] if pairs else 0.0
    
    def _weighted_mean(self, values: List[float], weights: List[float]) -> float:
        """Calculate weighted mean."""
        if not values or not weights or len(values) != len(weights):
            return statistics.mean(values) if values else 0.0
        
        total_weight = sum(weights)
        if total_weight == 0:
            return statistics.mean(values)
        
        return sum(v * w for v, w in zip(values, weights)) / total_weight
    
    def _calculate_confidence_interval(self, values: List[float], confidence: float = 0.95) -> Tuple[float, float]:
        """Calculate confidence interval for values."""
        if len(values) < 2:
            return (values[0] if values else 0.0, values[0] if values else 0.0)
        
        mean_val = statistics.mean(values)
        if len(values) == 1:
            return (mean_val, mean_val)
        
        try:
            stdev = statistics.stdev(values)
            # Use t-distribution approximation (simplified for n>=2)
            # For 95% confidence, approximate multiplier
            n = len(values)
            if n >= 30:
                multiplier = 1.96  # Normal distribution
            elif n >= 10:
                multiplier = 2.0   # Conservative estimate
            else:
                multiplier = 2.5   # More conservative for small samples
            
            margin = multiplier * stdev / math.sqrt(n)
            return (mean_val - margin, mean_val + margin)
        except:
            return (min(values), max(values))
    
    def _calculate_source_consistency(self, all_source_data: Dict[str, List[Dict]], 
                                     num_hours: int) -> Dict[str, float]:
        """Calculate how consistent each source is with others."""
        consistency_scores = {}
        
        for source_name in all_source_data.keys():
            deviations = []
            
            for hour_idx in range(num_hours):
                source_vals = {}
                for name, data in all_source_data.items():
                    if hour_idx < len(data):
                        try:
                            source_vals[name] = {
                                'temp': float(data[hour_idx].get('temperature', 0)),
                                'precip': float(data[hour_idx].get('precipitation', 0)),
                                'wind': float(data[hour_idx].get('wind_speed', 0)),
                                'humidity': float(data[hour_idx].get('humidity', 50))
                            }
                        except:
                            continue
                
                if source_name not in source_vals or len(source_vals) < 2:
                    continue
                
                # Calculate average of all other sources
                other_sources = {k: v for k, v in source_vals.items() if k != source_name}
                if not other_sources:
                    continue
                
                avg_temp = statistics.mean([v['temp'] for v in other_sources.values()])
                avg_precip = statistics.mean([v['precip'] for v in other_sources.values()])
                avg_wind = statistics.mean([v['wind'] for v in other_sources.values()])
                avg_humidity = statistics.mean([v['humidity'] for v in other_sources.values()])
                
                # Calculate normalized deviation
                source_val = source_vals[source_name]
                temp_dev = abs(source_val['temp'] - avg_temp) / max(abs(avg_temp), 1.0)
                precip_dev = abs(source_val['precip'] - avg_precip) / max(avg_precip + 0.1, 0.1)
                wind_dev = abs(source_val['wind'] - avg_wind) / max(avg_wind + 0.1, 0.1)
                humidity_dev = abs(source_val['humidity'] - avg_humidity) / 100.0
                
                # Combined deviation (lower is better)
                combined_dev = (temp_dev + precip_dev + wind_dev + humidity_dev) / 4.0
                deviations.append(combined_dev)
            
            if deviations:
                # Consistency score: 1.0 = perfect, 0.0 = very inconsistent
                avg_deviation = statistics.mean(deviations)
                consistency_scores[source_name] = max(0.0, 1.0 - min(avg_deviation, 1.0))
            else:
                consistency_scores[source_name] = 0.5  # Default if can't calculate
        
        return consistency_scores
    
    def aggregate_weather_data(self) -> WeatherData:
        """Fetch from all sources and aggregate the results with improved accuracy."""
        print("Fetching weather data from multiple sources...")
        
        # Fetch from all sources in parallel (simulated with sequential calls)
        sources = {
            'Open-Meteo': self.fetch_open_meteo(),
            'WeatherAPI': self.fetch_weatherapi(),
            'OpenWeatherMap': self.fetch_openweathermap(),
            '7Timer': self.fetch_7timer(),
            'wttr.in': self.fetch_wttr()
        }
        
        # Filter successful sources
        successful_sources = {k: v for k, v in sources.items() if v is not None}
        
        print(f"Successfully fetched from {len(successful_sources)} sources: {list(successful_sources.keys())}")
        
        if len(successful_sources) < 2:
            raise Exception("Failed to fetch from at least 2 weather sources")
        
        # Aggregate data for each hour
        weather_data = WeatherData()
        weather_data.sources_used = list(successful_sources.keys())
        weather_data.reliability_score = len(successful_sources) / 5.0
        
        # Find the minimum number of hours available across all sources
        source_lengths = []
        for source_name, source_data in successful_sources.items():
            if not isinstance(source_data, list):
                raise Exception(f"Source {source_name} returned invalid data type: {type(source_data)}")
            source_lengths.append(len(source_data))
        
        if not source_lengths:
            raise Exception("No valid source data available")
        
        min_hours = min(source_lengths)
        
        # Calculate source consistency scores
        consistency_scores = self._calculate_source_consistency(successful_sources, min_hours)
        weather_data.source_consistency_scores = consistency_scores
        
        print(f"Source consistency scores: {consistency_scores}")
        
        for hour_idx in range(min_hours):
            temp_data = []  # List of (value, weight) tuples
            precips = []
            winds = []
            humidities = []
            conditions = []
            
            for source_name, source_data in successful_sources.items():
                if hour_idx < len(source_data):
                    try:
                        hour_data = source_data[hour_idx]
                        
                        # Safely convert all numeric values to float, handling None and string values
                        def safe_float(value, default=0.0):
                            if value is None:
                                return default
                            try:
                                return float(value)
                            except (ValueError, TypeError):
                                return default
                        
                        temp_val = safe_float(hour_data.get('temperature'))
                        precip_val = safe_float(hour_data.get('precipitation'), 0.0)
                        wind_val = safe_float(hour_data.get('wind_speed'), 0.0)
                        humidity_val = safe_float(hour_data.get('humidity'), 50.0)
                        condition_val = hour_data.get('condition', 'Unknown')
                        
                        # Validate reasonable ranges and store with weights
                        if -50 <= temp_val <= 60:  # Reasonable temperature range
                            # Weight = base weight * consistency score
                            base_weight = self.source_weights.get(source_name, 1.0)
                            consistency = consistency_scores.get(source_name, 0.5)
                            weight = base_weight * consistency
                            temp_data.append((temp_val, weight))
                        
                        if 0 <= precip_val <= 500:  # Reasonable precipitation (mm)
                            precips.append(precip_val)
                        
                        if 0 <= wind_val <= 100:  # Reasonable wind speed (m/s)
                            winds.append(wind_val)
                        
                        if 0 <= humidity_val <= 100:  # Humidity percentage
                            humidities.append(humidity_val)
                        
                        conditions.append(condition_val)
                    except Exception as e:
                        print(f"Warning: Error processing {source_name} hour {hour_idx}: {e}")
                        continue
            
            # Skip if no valid data collected
            if not temp_data:
                continue
            
            # Extract temps and weights separately for outlier removal
            temps = [t[0] for t in temp_data]
            temp_weights = [t[1] for t in temp_data]
            
            # Remove outliers for more accurate aggregation
            temps_clean = self._remove_outliers(temps)
            precips_clean = self._remove_outliers(precips)
            winds_clean = self._remove_outliers(winds)
            humidities_clean = self._remove_outliers(humidities)
            
            # Match weights to cleaned temps (keep weights for values that weren't removed)
            if len(temps_clean) < len(temps):
                # Rebuild temp_data with cleaned values
                temp_data_clean = [(t, w) for t, w in zip(temps, temp_weights) if t in temps_clean]
                temps_clean = [t[0] for t in temp_data_clean]
                temp_weights_clean = [t[1] for t in temp_data_clean]
            else:
                temp_weights_clean = temp_weights
            
            # Use weighted median for temperature (most robust with weights)
            # Fall back to trimmed mean if we don't have enough data
            if len(temps_clean) >= 2 and len(temp_weights_clean) == len(temps_clean):
                temp_final = self._weighted_median(temps_clean, temp_weights_clean)
            else:
                temp_final = self._trimmed_mean(temps_clean if temps_clean else temps)
            
            precip_final = self._trimmed_mean(precips_clean if precips_clean else precips) if precips else 0.0
            wind_final = self._trimmed_mean(winds_clean if winds_clean else winds) if winds else 0.0
            humidity_final = self._trimmed_mean(humidities_clean if humidities_clean else humidities) if humidities else 50.0
            
            # Calculate confidence intervals
            temp_ci = self._calculate_confidence_interval(temps_clean if temps_clean else temps)
            precip_ci = self._calculate_confidence_interval(precips_clean if precips_clean else precips) if precips else (0.0, 0.0)
            wind_ci = self._calculate_confidence_interval(winds_clean if winds_clean else winds) if winds else (0.0, 0.0)
            humidity_ci = self._calculate_confidence_interval(humidities_clean if humidities_clean else humidities) if humidities else (50.0, 50.0)
            
            # Calculate standard deviation for uncertainty measure
            temp_std = statistics.stdev(temps_clean if temps_clean else temps) if len(temps) > 1 else 0.0
            
            # Calculate consensus values with improved accuracy
            aggregated_hour = {
                'hour': hour_idx,
                'temperature': round(temp_final, 1),
                'precipitation': round(precip_final, 2),
                'wind_speed': round(wind_final, 1),
                'humidity': round(humidity_final, 1),
                'condition': max(set(conditions), key=conditions.count) if conditions else 'Unknown',
                'temp_range': (round(min(temps), 1), round(max(temps), 1)),
                'temp_confidence': (round(temp_ci[0], 1), round(temp_ci[1], 1)),
                'temp_uncertainty': round(temp_std, 1),
                'sources_count': len(temps)
            }
            
            weather_data.hourly_data.append(aggregated_hour)
        
        return weather_data
    
    @staticmethod
    def _decode_wmo_code(code: int) -> str:
        """Decode WMO weather codes to descriptions."""
        wmo_codes = {
            0: 'Clear sky',
            1: 'Mainly clear',
            2: 'Partly cloudy',
            3: 'Overcast',
            45: 'Foggy',
            48: 'Foggy',
            51: 'Light drizzle',
            53: 'Moderate drizzle',
            55: 'Dense drizzle',
            61: 'Slight rain',
            63: 'Moderate rain',
            65: 'Heavy rain',
            71: 'Slight snow',
            73: 'Moderate snow',
            75: 'Heavy snow',
            77: 'Snow grains',
            80: 'Slight rain showers',
            81: 'Moderate rain showers',
            82: 'Violent rain showers',
            85: 'Slight snow showers',
            86: 'Heavy snow showers',
            95: 'Thunderstorm',
            96: 'Thunderstorm with hail',
            99: 'Thunderstorm with hail'
        }
        return wmo_codes.get(code, 'Unknown')
    
    @staticmethod
    def _estimate_precip_from_weather(weather: str) -> float:
        """Estimate precipitation from weather description."""
        weather_lower = weather.lower()
        if 'rain' in weather_lower or 'shower' in weather_lower:
            return 2.0
        elif 'drizzle' in weather_lower:
            return 0.5
        elif 'snow' in weather_lower:
            return 1.0
        return 0.0


if __name__ == "__main__":
    # Test the weather sources
    import os
    lat = float(os.getenv('LOCATION_LAT', '48.8566'))
    lon = float(os.getenv('LOCATION_LON', '2.3522'))
    
    weather = WeatherSources(lat, lon)
    data = weather.aggregate_weather_data()
    
    print(f"\nReliability Score: {data.reliability_score}")
    print(f"Sources Used: {data.sources_used}")
    print("\nNext 10 hours forecast:")
    for hour in data.hourly_data:
        print(f"Hour +{hour['hour']}: {hour['temperature']}°C, {hour['condition']}, "
              f"Precip: {hour['precipitation']}mm, Wind: {hour['wind_speed']}m/s")

