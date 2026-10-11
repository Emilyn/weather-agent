"""
Unit tests for weather source alignment and aggregation.
Uses canned API responses, so no network or API keys are needed.

Run with: python -m unittest discover tests
"""

import os
import sys
import unittest
from datetime import datetime, timedelta
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from weather_sources import WeatherSources  # noqa: E402


# Location is UTC+2; the agent runs at 06:00 local time (04:00 UTC).
# Every source reports temperature = 10 + local hour, so aligned data agrees.
LOCAL_NOW = datetime(2026, 9, 23, 6, 0)
UTC_OFFSET_SECONDS = 2 * 3600


def open_meteo_response():
    times = [datetime(2026, 9, 23) + timedelta(hours=h) for h in range(48)]
    n = len(times)
    return {
        'utc_offset_seconds': UTC_OFFSET_SECONDS,
        'hourly': {
            'time': [t.strftime('%Y-%m-%dT%H:%M') for t in times],
            'temperature_2m': [10 + t.hour for t in times],
            'precipitation': [0.0] * n,
            'rain': [0.0] * n,
            'snowfall': [0.0] * n,
            'windspeed_10m': [36.0] * n,  # km/h
            'relativehumidity_2m': [60] * n,
            'weathercode': [0] * n,
        }
    }


def wttr_response():
    # 3-hourly, starting at local midnight
    return {
        'weather': [{
            'date': '2026-09-23',
            'hourly': [
                {
                    'time': str(h * 100),
                    'tempC': str(10 + h),
                    'precipMM': '0.0',
                    'totalSnow_cm': '0.0',
                    'windspeedKmph': '36',
                    'humidity': '60',
                    'weatherDesc': [{'value': 'Sunny'}],
                }
                for h in range(0, 24, 3)
            ]
        }]
    }


def fake_fetch(url, params=None, headers=None, method='GET', timeout=10,
               source_name="API", json_data=None):
    return {
        'Open-Meteo': open_meteo_response,
        'wttr.in': wttr_response,
    }[source_name]()


def point(hour, temperature, condition='Clear'):
    return {'time': datetime(2026, 9, 23, hour), 'temperature': temperature, 'precipitation': 0.0,
            'rain': 0.0, 'snow': 0.0, 'wind_speed': 3.0, 'humidity': 60.0, 'condition': condition}


class AlignToHoursTest(unittest.TestCase):
    def test_exact_match_used_as_is(self):
        aligned = WeatherSources._align_to_hours([point(6, 12.0)], [datetime(2026, 9, 23, 6)])
        self.assertEqual(aligned[0]['temperature'], 12.0)

    def test_interpolates_between_3_hourly_points(self):
        # Real Stockholm case: wttr.in 18:00 = 13°C, 21:00 = 10°C. Taking the nearest
        # point at 20:00 would report 10°C; interpolation gives 11°C
        items = [point(18, 13.0, 'Sunny'), point(21, 10.0, 'Clear')]
        targets = [datetime(2026, 9, 23, h) for h in (19, 20)]
        aligned = WeatherSources._align_to_hours(items, targets)
        self.assertAlmostEqual(aligned[0]['temperature'], 12.0)
        self.assertAlmostEqual(aligned[1]['temperature'], 11.0)
        self.assertEqual(aligned[0]['condition'], 'Sunny')
        self.assertEqual(aligned[1]['condition'], 'Clear')
        self.assertEqual(aligned[1]['time'], datetime(2026, 9, 23, 20))

    def test_no_interpolation_across_large_gaps(self):
        items = [point(0, 5.0), point(12, 15.0)]
        self.assertEqual(WeatherSources._align_to_hours(items, [datetime(2026, 9, 23, 6)]), [None])

    def test_returns_none_outside_coverage(self):
        aligned = WeatherSources._align_to_hours([point(21, 10.0)], [datetime(2026, 9, 23, 23)])
        self.assertEqual(aligned, [None])


class UtcOffsetTest(unittest.TestCase):
    def test_longitude_estimate_when_no_source_reports_offset(self):
        sources = WeatherSources(lat=40.7, lon=-74.0)
        sources._estimate_utc_offset_from_longitude()
        self.assertEqual(sources.utc_offset, timedelta(hours=-5))


class AggregateWeatherDataTest(unittest.TestCase):
    @patch('weather_sources.fetch_api_data', side_effect=fake_fetch)
    def test_sources_are_aligned_by_local_time(self, _):
        sources = WeatherSources(lat=48.85, lon=2.35)
        with patch.object(WeatherSources, '_location_now', return_value=LOCAL_NOW):
            data = sources.aggregate_weather_data()

        self.assertEqual(set(data.sources_used), {'Open-Meteo', 'wttr.in'})

        first = data.hourly_data[0]
        self.assertEqual(first['time'], '2026-09-23 06:00')
        # Open-Meteo and wttr.in both report 16°C at 06:00 local; index-based
        # alignment would have mixed in wttr.in's midnight reading (10°C)
        self.assertEqual(first['temperature'], 16.0)
        # 20:00 falls between wttr.in's 18:00 and 21:00 points; interpolated, both sources agree
        at_20 = next(h for h in data.hourly_data if h['time'].endswith('20:00'))
        self.assertEqual(at_20['temperature'], 30.0)
        self.assertEqual(at_20['sources_count'], 2)

    @patch('weather_sources.fetch_api_data', side_effect=fake_fetch)
    def test_morning_run_covers_the_whole_day(self, _):
        sources = WeatherSources(lat=59.33, lon=18.07)
        with patch.object(WeatherSources, '_location_now', return_value=LOCAL_NOW):
            data = sources.aggregate_weather_data()
        # 06:00 through 23:00
        self.assertEqual(len(data.hourly_data), 18)
        self.assertEqual(data.hourly_data[-1]['time'], '2026-09-23 23:00')

    @patch('weather_sources.fetch_api_data', side_effect=fake_fetch)
    def test_open_meteo_wind_converted_to_ms(self, _):
        sources = WeatherSources(lat=48.85, lon=2.35)
        items = sources.fetch_open_meteo()
        self.assertAlmostEqual(items[0]['wind_speed'], 10.0)
        self.assertEqual(sources.utc_offset, timedelta(hours=2))

    @patch('weather_sources.fetch_api_data', side_effect=fake_fetch)
    def test_late_run_covers_rest_of_day(self, _):
        sources = WeatherSources(lat=48.85, lon=2.35)
        late = datetime(2026, 9, 23, 20, 0)
        with patch.object(WeatherSources, '_location_now', return_value=late):
            data = sources.aggregate_weather_data()
        self.assertEqual([h['time'][11:] for h in data.hourly_data], ['20:00', '21:00', '22:00', '23:00'])


if __name__ == '__main__':
    unittest.main()
