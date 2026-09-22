"""
Weather data fetching from multiple free sources.
Aggregates data from 5 different weather APIs for reliability.

Every source is normalized to timestamps in the location's local time, then
aligned to the same target hours before aggregation. Sources report at
different resolutions (hourly vs 3-hourly) and start points, so combining
them by list index would mix forecasts for different times.
"""

import requests
import statistics
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple
import json
import math
from utils import fetch_api_data, safe_float, kmh_to_ms


FORECAST_HOURS = 10
# 3-hourly sources are matched to the nearest forecast point within this window
MATCH_TOLERANCE = timedelta(minutes=90)


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
        # Location's offset from UTC, learned from the first source that reports it
        self.utc_offset: Optional[timedelta] = None

        # Source reliability weights (based on typical API quality)
        # Higher weight = more reliable source
        self.source_weights = {
            'Open-Meteo': 1.0,      # High quality, free, no key needed
            'WeatherAPI': 1.2,       # Commercial API, generally accurate
            'OpenWeatherMap': 1.1,   # Well-established, reliable
            '7Timer': 0.8,           # Free but less detailed
            'wttr.in': 0.9           # Good coverage, free
        }

    def _set_utc_offset(self, offset: timedelta):
        """Record the location's UTC offset if no source has provided one yet."""
        if self.utc_offset is None:
            self.utc_offset = offset

    def _location_now(self) -> datetime:
        """Current time at the location (naive, truncated to the hour)."""
        utc_now = datetime.now(timezone.utc).replace(tzinfo=None)
        if self.utc_offset is None:
            self._estimate_utc_offset_from_longitude()
        local_now = utc_now + self.utc_offset
        return local_now.replace(minute=0, second=0, microsecond=0)

    def _estimate_utc_offset_from_longitude(self):
        """Last resort when no source reported an offset: solar time zone (15° per hour)."""
        self.utc_offset = timedelta(hours=round(self.lon / 15))
        print(f"Warning: location UTC offset unknown, estimating {self.utc_offset} from longitude")

    @staticmethod
    def _utc_offset_from_wttr(data: Dict) -> Optional[timedelta]:
        """
        Derive the UTC offset from wttr.in's current observation, which gives both
        local time ("2026-09-23 06:12 AM") and UTC time of day ("04:12 AM").
        """
        try:
            current = data['current_condition'][0]
            local = datetime.strptime(current['localObsDateTime'], '%Y-%m-%d %I:%M %p')
            utc = datetime.strptime(current['observation_time'], '%I:%M %p')
        except (KeyError, IndexError, TypeError, ValueError):
            return None
        minutes = (local.hour * 60 + local.minute) - (utc.hour * 60 + utc.minute)
        # The UTC time has no date, so wrap across midnight into the valid -12h..+14h range
        if minutes < -12 * 60:
            minutes += 24 * 60
        elif minutes > 14 * 60:
            minutes -= 24 * 60
        return timedelta(minutes=round(minutes / 15) * 15)

    @staticmethod
    def _align_to_hours(items: List[Dict], target_times: List[datetime]) -> List[Optional[Dict]]:
        """For each target hour, pick the nearest forecast item within MATCH_TOLERANCE."""
        aligned = []
        for target in target_times:
            best = min(items, key=lambda item: abs(item['time'] - target), default=None)
            if best is not None and abs(best['time'] - target) <= MATCH_TOLERANCE:
                aligned.append(best)
            else:
                aligned.append(None)
        return aligned

    def fetch_open_meteo(self) -> Optional[List[Dict]]:
        """Fetch from Open-Meteo (no API key needed). Times are location-local."""
        data = fetch_api_data(
            url="https://api.open-meteo.com/v1/forecast",
            params={
                'latitude': self.lat,
                'longitude': self.lon,
                'hourly': 'temperature_2m,precipitation,rain,snowfall,windspeed_10m,relativehumidity_2m,weathercode',
                'forecast_days': 2,  # Covers runs late in the day
                'timezone': 'auto'
            },
            timeout=self.timeout,
            source_name="Open-Meteo"
        )
        if not data:
            return None

        if 'utc_offset_seconds' in data:
            self._set_utc_offset(timedelta(seconds=data['utc_offset_seconds']))

        hourly = data['hourly']
        return [
            {
                'time': datetime.fromisoformat(time),
                'temperature': temp,
                'precipitation': precip,
                'rain': rain,
                'snow': snow,
                'wind_speed': kmh_to_ms(wind) if wind is not None else None,
                'humidity': humidity,
                'condition': self._decode_wmo_code(code)
            }
            for time, temp, precip, rain, snow, wind, humidity, code in zip(
                hourly['time'],
                hourly['temperature_2m'],
                hourly['precipitation'],
                hourly['rain'],
                hourly['snowfall'],
                hourly['windspeed_10m'],
                hourly['relativehumidity_2m'],
                hourly['weathercode']
            )
        ]

    def fetch_weatherapi(self) -> Optional[List[Dict]]:
        """Fetch from WeatherAPI.com (free tier). Times are location-local."""
        if not self.weatherapi_key:
            return None

        data = fetch_api_data(
            url="http://api.weatherapi.com/v1/forecast.json",
            params={
                'key': self.weatherapi_key,
                'q': f"{self.lat},{self.lon}",
                'days': 2,  # Covers runs late in the day
                'aqi': 'no'
            },
            timeout=self.timeout,
            source_name="WeatherAPI"
        )
        if not data:
            return None

        location = data.get('location', {})
        if 'localtime_epoch' in location and 'localtime' in location:
            local = datetime.strptime(location['localtime'], '%Y-%m-%d %H:%M')
            utc = datetime.fromtimestamp(location['localtime_epoch'], timezone.utc).replace(tzinfo=None)
            # Round to the nearest 15 minutes (all real offsets are multiples of 15)
            self._set_utc_offset(timedelta(minutes=round((local - utc).total_seconds() / 900) * 15))

        return [
            {
                'time': datetime.strptime(hour['time'], '%Y-%m-%d %H:%M'),
                'temperature': hour['temp_c'],
                'precipitation': hour['precip_mm'],
                'rain': hour.get('precip_mm', 0) if hour.get('snow_cm', 0) == 0 else 0,
                'snow': hour.get('snow_cm', 0) * 10,  # Convert cm to mm for consistency
                'wind_speed': kmh_to_ms(hour['wind_kph']),
                'humidity': hour['humidity'],
                'condition': hour['condition']['text']
            }
            for day in data['forecast']['forecastday']
            for hour in day['hour']
        ]

    def fetch_openweathermap(self) -> Optional[List[Dict]]:
        """Fetch from OpenWeatherMap (free tier, 3-hourly). Times are UTC epochs."""
        if not self.openweather_key:
            return None

        data = fetch_api_data(
            url="https://api.openweathermap.org/data/2.5/forecast",
            params={
                'lat': self.lat,
                'lon': self.lon,
                'appid': self.openweather_key,
                'units': 'metric',
                'cnt': 10
            },
            timeout=self.timeout,
            source_name="OpenWeatherMap"
        )
        if not data:
            return None

        offset = timedelta(seconds=data.get('city', {}).get('timezone', 0))
        self._set_utc_offset(offset)

        return [
            {
                'time': datetime.fromtimestamp(item['dt'], timezone.utc).replace(tzinfo=None) + offset,
                'temperature': item['main']['temp'],
                'precipitation': item.get('rain', {}).get('3h', 0) / 3,  # Convert 3h to 1h avg
                'rain': item.get('rain', {}).get('3h', 0) / 3,
                'snow': item.get('snow', {}).get('3h', 0) / 3,  # Convert 3h to 1h avg
                'wind_speed': item['wind']['speed'],
                'humidity': item['main']['humidity'],
                'condition': item['weather'][0]['description']
            }
            for item in data['list']
        ]

    def fetch_7timer(self) -> Optional[List[Dict]]:
        """Fetch from 7Timer (no API key needed, 3-hourly). Times are offsets from a UTC init time."""
        data = fetch_api_data(
            url="http://www.7timer.info/bin/api.pl",
            params={
                'lon': self.lon,
                'lat': self.lat,
                'product': 'civil',
                'output': 'json'
            },
            timeout=self.timeout,
            source_name="7Timer"
        )
        if not data:
            return None

        if self.utc_offset is None:
            print("7Timer skipped: location UTC offset unknown, cannot convert its UTC times")
            return None

        init = datetime.strptime(data['init'], '%Y%m%d%H') + self.utc_offset
        return [
            {
                'time': init + timedelta(hours=item['timepoint']),
                'temperature': item['temp2m'],
                'precipitation': self._estimate_precip_from_weather(item['weather']),
                'rain': self._estimate_rain_from_weather(item['weather']),
                'snow': self._estimate_snow_from_weather(item['weather']),
                # 7Timer's 'civil' product reports wind speed on a 1-8 scale, not km/h
                'wind_speed': self._7timer_wind_class_to_ms(item['wind10m']['speed']),
                'humidity': safe_float(str(item.get('rh2m', '50')).rstrip('%'), 50.0),
                'condition': item['weather']
            }
            for item in data['dataseries']
        ]

    def fetch_wttr(self) -> Optional[List[Dict]]:
        """Fetch from wttr.in (no API key needed, 3-hourly). Times are location-local."""
        data = fetch_api_data(
            url=f"https://wttr.in/{self.lat},{self.lon}",
            params={'format': 'j1'},
            timeout=self.timeout,
            source_name="wttr.in"
        )
        if not data:
            return None

        offset = self._utc_offset_from_wttr(data)
        if offset is not None:
            self._set_utc_offset(offset)

        return [
            {
                # 'time' is "0", "300", ..., "2100" (HHMM) on the given local date
                'time': datetime.strptime(day['date'], '%Y-%m-%d') + timedelta(hours=int(hour['time']) // 100),
                'temperature': safe_float(hour['tempC']),
                'precipitation': safe_float(hour['precipMM']),
                'rain': safe_float(hour.get('precipMM', 0)) if 'snow' not in hour.get('weatherDesc', [{}])[0].get('value', '').lower() else 0,
                'snow': safe_float(hour.get('totalSnow_cm', 0)) * 10,  # Convert cm to mm
                'wind_speed': kmh_to_ms(safe_float(hour['windspeedKmph'])),
                'humidity': safe_float(hour['humidity']),
                'condition': hour['weatherDesc'][0]['value']
            }
            for day in data['weather']
            for hour in day['hourly']
        ]

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
                    if hour_idx < len(data) and data[hour_idx] is not None:
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
            'wttr.in': self.fetch_wttr()
        }
        # 7Timer reports UTC times, so fetch it last, once another source has told us
        # the location's UTC offset (or fall back to a longitude-based estimate)
        if self.utc_offset is None:
            self._estimate_utc_offset_from_longitude()
        sources['7Timer'] = self.fetch_7timer()
        
        # Align every source to the same local target hours; drop sources with no overlap
        start = self._location_now()
        target_times = [start + timedelta(hours=i) for i in range(FORECAST_HOURS)]
        successful_sources = {}
        for name, items in sources.items():
            if not items:
                continue
            aligned = self._align_to_hours(items, target_times)
            if any(item is not None for item in aligned):
                successful_sources[name] = aligned
            else:
                print(f"{name} skipped: no forecast points near {start:%Y-%m-%d %H:%M}")
        
        print(f"Successfully fetched from {len(successful_sources)} sources: {list(successful_sources.keys())}")
        
        if len(successful_sources) < 2:
            raise Exception("Failed to fetch from at least 2 weather sources")
        
        # Aggregate data for each hour
        weather_data = WeatherData()
        weather_data.sources_used = list(successful_sources.keys())
        weather_data.reliability_score = len(successful_sources) / 5.0
        
        num_hours = len(target_times)
        
        # Calculate source consistency scores
        consistency_scores = self._calculate_source_consistency(successful_sources, num_hours)
        weather_data.source_consistency_scores = consistency_scores
        
        print(f"Source consistency scores: {consistency_scores}")
        
        for hour_idx in range(num_hours):
            temp_data = []  # List of (value, weight) tuples
            precips = []
            rains = []
            snows = []
            winds = []
            humidities = []
            conditions = []
            
            for source_name, source_data in successful_sources.items():
                if source_data[hour_idx] is not None:
                    try:
                        hour_data = source_data[hour_idx]
                        
                        # Safely convert all numeric values to float, handling None and string values
                        temp_val = safe_float(hour_data.get('temperature'))
                        precip_val = safe_float(hour_data.get('precipitation'), 0.0)
                        rain_val = safe_float(hour_data.get('rain'), 0.0)
                        snow_val = safe_float(hour_data.get('snow'), 0.0)
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
                        
                        if 0 <= rain_val <= 500:  # Reasonable rain (mm)
                            rains.append(rain_val)
                        
                        if 0 <= snow_val <= 500:  # Reasonable snow (mm)
                            snows.append(snow_val)
                        
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
            rains_clean = self._remove_outliers(rains)
            snows_clean = self._remove_outliers(snows)
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
            rain_final = self._trimmed_mean(rains_clean if rains_clean else rains) if rains else 0.0
            snow_final = self._trimmed_mean(snows_clean if snows_clean else snows) if snows else 0.0
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
                'time': target_times[hour_idx].strftime('%Y-%m-%d %H:%M'),
                'temperature': round(temp_final, 1),
                'precipitation': round(precip_final, 2),
                'rain': round(rain_final, 2),
                'snow': round(snow_final, 2),
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
    def _7timer_wind_class_to_ms(wind_class: int) -> float:
        """Convert 7Timer's 1-8 wind speed class to the midpoint of its m/s range."""
        class_midpoints = {1: 0.15, 2: 1.85, 3: 5.7, 4: 9.4, 5: 14.0, 6: 20.85, 7: 28.55, 8: 32.6}
        return class_midpoints.get(int(safe_float(wind_class, 1)), 0.15)
    
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
    
    @staticmethod
    def _estimate_rain_from_weather(weather: str) -> float:
        """Estimate rain from weather description."""
        weather_lower = weather.lower()
        if 'rain' in weather_lower or 'shower' in weather_lower:
            return 2.0
        elif 'drizzle' in weather_lower:
            return 0.5
        return 0.0
    
    @staticmethod
    def _estimate_snow_from_weather(weather: str) -> float:
        """Estimate snow from weather description."""
        weather_lower = weather.lower()
        if 'snow' in weather_lower:
            if 'heavy' in weather_lower:
                return 5.0
            elif 'light' in weather_lower or 'slight' in weather_lower:
                return 1.0
            else:
                return 2.0
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

