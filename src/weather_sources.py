"""
Weather data fetching from multiple free sources.
Aggregates data from 5 different weather APIs for reliability.
"""

import requests
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import json


class WeatherData:
    """Container for aggregated weather data."""
    
    def __init__(self):
        self.hourly_data = []  # List of hourly forecasts
        self.sources_used = []
        self.reliability_score = 0.0
    
    def to_dict(self):
        return {
            'hourly_data': self.hourly_data,
            'sources_used': self.sources_used,
            'reliability_score': self.reliability_score
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
    
    def aggregate_weather_data(self) -> WeatherData:
        """Fetch from all sources and aggregate the results."""
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
        min_hours = min(len(data) for data in successful_sources.values())
        
        for hour_idx in range(min_hours):
            temps = []
            precips = []
            winds = []
            humidities = []
            conditions = []
            
            for source_name, source_data in successful_sources.items():
                if hour_idx < len(source_data):
                    # Convert all numeric values to float to avoid type comparison errors
                    temps.append(float(source_data[hour_idx]['temperature']))
                    precips.append(float(source_data[hour_idx]['precipitation']))
                    winds.append(float(source_data[hour_idx]['wind_speed']))
                    humidities.append(float(source_data[hour_idx]['humidity']))
                    conditions.append(source_data[hour_idx]['condition'])
            
            # Calculate consensus values
            aggregated_hour = {
                'hour': hour_idx,
                'temperature': round(statistics.median(temps), 1),
                'precipitation': round(statistics.median(precips), 1),
                'wind_speed': round(statistics.median(winds), 1),
                'humidity': round(statistics.median(humidities), 1),
                'condition': max(set(conditions), key=conditions.count),  # Most common
                'temp_range': (round(min(temps), 1), round(max(temps), 1))
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

