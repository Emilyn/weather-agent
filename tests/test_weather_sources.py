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
        # 06:12 local = 04:12 UTC, so wttr.in alone reveals the +2h offset
        'current_condition': [{
            'localObsDateTime': '2026-09-23 06:12 AM',
            'observation_time': '04:12 AM',
        }],
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


def seven_timer_response():
    # 3-hourly offsets from a UTC init time (00 UTC = 02:00 local)
    return {
        'init': '2026092300',
        'dataseries': [
            {
                'timepoint': tp,
                'temp2m': 10 + (2 + tp) % 24,
                'weather': 'clearday',
                'wind10m': {'direction': 'N', 'speed': 3},
                'rh2m': '60%',
            }
            for tp in range(3, 25, 3)
        ]
    }


def fake_fetch(url, params=None, headers=None, method='GET', timeout=10,
               source_name="API", json_data=None):
    return {
        'Open-Meteo': open_meteo_response,
        'wttr.in': wttr_response,
        '7Timer': seven_timer_response,
    }[source_name]()


class AlignToHoursTest(unittest.TestCase):
    def test_picks_nearest_point_within_tolerance(self):
        items = [{'time': datetime(2026, 9, 23, h)} for h in (3, 6, 9)]
        targets = [datetime(2026, 9, 23, h) for h in (6, 7, 8)]
        aligned = WeatherSources._align_to_hours(items, targets)
        self.assertEqual([a['time'].hour for a in aligned], [6, 6, 9])

    def test_returns_none_outside_tolerance(self):
        items = [{'time': datetime(2026, 9, 23, 0)}]
        aligned = WeatherSources._align_to_hours(items, [datetime(2026, 9, 23, 6)])
        self.assertEqual(aligned, [None])


def fetch_without_open_meteo(url, params=None, headers=None, method='GET', timeout=10,
                             source_name="API", json_data=None):
    if source_name == 'Open-Meteo':
        return None  # simulate an outage
    return fake_fetch(url, params, headers, method, timeout, source_name, json_data)


class UtcOffsetTest(unittest.TestCase):
    def test_offset_from_wttr(self):
        self.assertEqual(WeatherSources._utc_offset_from_wttr(wttr_response()), timedelta(hours=2))

    def test_offset_from_wttr_across_midnight(self):
        data = {'current_condition': [{'localObsDateTime': '2026-09-23 12:30 AM',
                                       'observation_time': '10:30 PM'}]}
        self.assertEqual(WeatherSources._utc_offset_from_wttr(data), timedelta(hours=2))
        data = {'current_condition': [{'localObsDateTime': '2026-09-22 08:00 PM',
                                       'observation_time': '03:00 AM'}]}
        self.assertEqual(WeatherSources._utc_offset_from_wttr(data), timedelta(hours=-7))

    def test_offset_from_wttr_missing_data(self):
        self.assertIsNone(WeatherSources._utc_offset_from_wttr({}))

    def test_longitude_estimate_when_no_source_reports_offset(self):
        sources = WeatherSources(lat=40.7, lon=-74.0)
        sources._estimate_utc_offset_from_longitude()
        self.assertEqual(sources.utc_offset, timedelta(hours=-5))


class AggregateWeatherDataTest(unittest.TestCase):
    @patch('weather_sources.fetch_api_data', side_effect=fetch_without_open_meteo)
    def test_works_without_open_meteo_or_api_keys(self, _):
        # Only keyless sources besides Open-Meteo: wttr.in must supply the offset for 7Timer
        sources = WeatherSources(lat=48.85, lon=2.35)
        with patch.object(WeatherSources, '_location_now', return_value=LOCAL_NOW):
            data = sources.aggregate_weather_data()
        self.assertEqual(set(data.sources_used), {'wttr.in', '7Timer'})
        self.assertEqual(sources.utc_offset, timedelta(hours=2))
        self.assertEqual(data.hourly_data[0]['time'], '2026-09-23 06:00')

    @patch('weather_sources.fetch_api_data', side_effect=fake_fetch)
    def test_sources_are_aligned_by_local_time(self, _):
        sources = WeatherSources(lat=48.85, lon=2.35)
        with patch.object(WeatherSources, '_location_now', return_value=LOCAL_NOW):
            data = sources.aggregate_weather_data()

        self.assertEqual(set(data.sources_used), {'Open-Meteo', 'wttr.in', '7Timer'})
        self.assertEqual(len(data.hourly_data), 10)

        first = data.hourly_data[0]
        self.assertEqual(first['time'], '2026-09-23 06:00')
        # Open-Meteo and wttr.in both report 16°C at 06:00 local; index-based
        # alignment would have mixed in wttr.in's midnight reading (10°C)
        self.assertEqual(first['temperature'], 16.0)
        self.assertEqual(data.hourly_data[9]['time'], '2026-09-23 15:00')

    @patch('weather_sources.fetch_api_data', side_effect=fake_fetch)
    def test_open_meteo_wind_converted_to_ms(self, _):
        sources = WeatherSources(lat=48.85, lon=2.35)
        items = sources.fetch_open_meteo()
        self.assertAlmostEqual(items[0]['wind_speed'], 10.0)
        self.assertEqual(sources.utc_offset, timedelta(hours=2))

    @patch('weather_sources.fetch_api_data', side_effect=fake_fetch)
    def test_7timer_times_converted_from_utc(self, _):
        sources = WeatherSources(lat=48.85, lon=2.35)
        sources.utc_offset = timedelta(hours=2)
        items = sources.fetch_7timer()
        self.assertEqual(items[0]['time'], datetime(2026, 9, 23, 5))
        self.assertAlmostEqual(items[0]['wind_speed'], 5.7)
        self.assertEqual(items[0]['humidity'], 60.0)

    @patch('weather_sources.fetch_api_data', side_effect=fake_fetch)
    def test_late_run_still_has_full_forecast(self, _):
        sources = WeatherSources(lat=48.85, lon=2.35)
        late = datetime(2026, 9, 23, 20, 0)
        with patch.object(WeatherSources, '_location_now', return_value=late):
            data = sources.aggregate_weather_data()
        # Open-Meteo now requests 2 days, so a 20:00 run still gets 10 hours
        self.assertEqual(len(data.hourly_data), 10)
        self.assertEqual(data.hourly_data[-1]['time'], '2026-09-24 05:00')


if __name__ == '__main__':
    unittest.main()
