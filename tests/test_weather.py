"""
Weather Service Unit Tests

Tests cover:
1. Weather condition mapping
2. Mom-friendly recommendation generation
3. RAG context generation
4. Cache behavior (unit tests only - no actual API calls)
"""
import pytest
from unittest.mock import patch, AsyncMock
import time

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from api.services.weather_service import (
    WeatherService,
    WeatherData,
    WeatherCondition,
    WMO_CODES,
    get_weather_service
)


# ============================================================
# FIXTURES
# ============================================================

@pytest.fixture
def weather_service():
    """Create a fresh weather service instance."""
    return WeatherService()


@pytest.fixture
def hot_weather():
    """Weather data for a hot sunny day."""
    return WeatherData(
        temperature_f=95.0,
        feels_like_f=100.0,
        humidity=60,
        precipitation_probability=10,
        precipitation_mm=0.0,
        weather_code=0,
        condition=WeatherCondition.SUNNY,
        uv_index=9.0,
        wind_speed_mph=5.0,
        is_daytime=True,
        mom_tip="It's hot! Look for splash pads and shaded playgrounds.",
        suggested_activities=["splash pads", "shaded playgrounds"],
        things_to_avoid=["unshaded playgrounds", "long hikes"],
        suggested_queries=["Find a splash pad near me"]
    )


@pytest.fixture
def rainy_weather():
    """Weather data for a rainy day."""
    return WeatherData(
        temperature_f=55.0,
        feels_like_f=52.0,
        humidity=85,
        precipitation_probability=80,
        precipitation_mm=5.0,
        weather_code=63,
        condition=WeatherCondition.RAINY,
        uv_index=2.0,
        wind_speed_mph=12.0,
        is_daytime=True,
        mom_tip="Rainy day - look for covered areas or indoor options!",
        suggested_activities=["covered pavilions", "indoor play"],
        things_to_avoid=["open playgrounds", "trails"],
        suggested_queries=["Parks with covered pavilions"]
    )


@pytest.fixture
def perfect_weather():
    """Weather data for a perfect day."""
    return WeatherData(
        temperature_f=72.0,
        feels_like_f=72.0,
        humidity=45,
        precipitation_probability=5,
        precipitation_mm=0.0,
        weather_code=1,
        condition=WeatherCondition.SUNNY,
        uv_index=5.0,
        wind_speed_mph=8.0,
        is_daytime=True,
        mom_tip="Perfect playground weather!",
        suggested_activities=["playgrounds", "trails", "picnics"],
        things_to_avoid=[],
        suggested_queries=["Best playgrounds nearby"]
    )


# ============================================================
# WMO CODE MAPPING TESTS
# ============================================================

class TestWMOCodeMapping:
    """Test weather code to condition mapping."""

    def test_clear_sky_codes(self):
        """Clear sky codes should map to SUNNY."""
        assert WMO_CODES[0] == WeatherCondition.SUNNY  # Clear sky
        assert WMO_CODES[1] == WeatherCondition.SUNNY  # Mainly clear

    def test_cloudy_codes(self):
        """Cloudy codes should map correctly."""
        assert WMO_CODES[2] == WeatherCondition.PARTLY_CLOUDY
        assert WMO_CODES[3] == WeatherCondition.CLOUDY

    def test_rain_codes(self):
        """Rain codes should map to RAINY."""
        rain_codes = [51, 53, 55, 61, 63, 65, 80, 81, 82]
        for code in rain_codes:
            assert WMO_CODES[code] == WeatherCondition.RAINY

    def test_snow_codes(self):
        """Snow codes should map to SNOWY."""
        snow_codes = [71, 73, 75]
        for code in snow_codes:
            assert WMO_CODES[code] == WeatherCondition.SNOWY

    def test_storm_codes(self):
        """Storm codes should map to STORMY."""
        storm_codes = [95, 96, 99]
        for code in storm_codes:
            assert WMO_CODES[code] == WeatherCondition.STORMY

    def test_fog_codes(self):
        """Fog codes should map to FOGGY."""
        fog_codes = [45, 48]
        for code in fog_codes:
            assert WMO_CODES[code] == WeatherCondition.FOGGY


# ============================================================
# RECOMMENDATION GENERATION TESTS
# ============================================================

class TestRecommendationGeneration:
    """Test mom-friendly recommendation generation."""

    def test_hot_weather_recommendations(self, weather_service):
        """Hot weather should recommend splash pads and shade."""
        mom_tip, activities, avoid, queries = weather_service._generate_recommendations(
            temp_f=95.0,
            feels_like_f=100.0,
            condition=WeatherCondition.SUNNY,
            uv_index=9.0,
            precip_prob=5,
            humidity=60
        )

        assert "hot" in mom_tip.lower() or "splash" in mom_tip.lower()
        assert "splash pads" in activities
        assert "shaded playgrounds" in activities or "shaded areas" in activities
        assert any("unshaded" in a or "metal slides" in a for a in avoid)

    def test_cold_weather_recommendations(self, weather_service):
        """Cold weather should recommend short visits and indoor options."""
        mom_tip, activities, avoid, queries = weather_service._generate_recommendations(
            temp_f=35.0,
            feels_like_f=28.0,
            condition=WeatherCondition.CLOUDY,
            uv_index=2.0,
            precip_prob=10,
            humidity=50
        )

        assert "bundle" in mom_tip.lower() or "cold" in mom_tip.lower()
        assert any("indoor" in a or "quick" in a for a in activities)

    def test_rainy_day_overrides(self, weather_service):
        """Rainy conditions should override temperature recommendations."""
        mom_tip, activities, avoid, queries = weather_service._generate_recommendations(
            temp_f=65.0,  # Cooler temp to avoid humidity override
            feels_like_f=65.0,
            condition=WeatherCondition.RAINY,
            uv_index=2.0,
            precip_prob=90,
            humidity=70  # Lower humidity to avoid humidity override
        )

        assert "rain" in mom_tip.lower()
        assert any("covered" in a or "indoor" in a for a in activities)
        assert "open playgrounds" in avoid or "trails" in avoid

    def test_perfect_weather_recommendations(self, weather_service):
        """Perfect weather should recommend everything."""
        mom_tip, activities, avoid, queries = weather_service._generate_recommendations(
            temp_f=72.0,
            feels_like_f=72.0,
            condition=WeatherCondition.SUNNY,
            uv_index=5.0,
            precip_prob=5,
            humidity=45
        )

        assert "perfect" in mom_tip.lower()
        assert "playgrounds" in activities
        assert "trails" in activities

    def test_high_uv_warning(self, weather_service):
        """High UV should add sunscreen warning."""
        mom_tip, activities, avoid, queries = weather_service._generate_recommendations(
            temp_f=80.0,
            feels_like_f=82.0,
            condition=WeatherCondition.SUNNY,
            uv_index=9.0,  # Very high
            precip_prob=0,
            humidity=40
        )

        assert "uv" in mom_tip.lower() or "sunscreen" in mom_tip.lower() or "shade" in mom_tip.lower()

    def test_humid_hot_warning(self, weather_service):
        """Hot and humid should warn about hydration."""
        mom_tip, activities, avoid, queries = weather_service._generate_recommendations(
            temp_f=88.0,
            feels_like_f=95.0,
            condition=WeatherCondition.PARTLY_CLOUDY,
            uv_index=6.0,
            precip_prob=20,
            humidity=85  # Very humid
        )

        assert "humid" in mom_tip.lower() or "hydrat" in mom_tip.lower()


# ============================================================
# RAG CONTEXT GENERATION TESTS
# ============================================================

class TestRAGContextGeneration:
    """Test RAG prompt context generation."""

    def test_context_includes_temperature(self, weather_service, hot_weather):
        """Context should include temperature."""
        context = weather_service.get_weather_context_for_rag(hot_weather)

        assert "95°F" in context
        assert "100°F" in context  # feels like

    def test_context_includes_condition(self, weather_service, rainy_weather):
        """Context should include weather condition."""
        context = weather_service.get_weather_context_for_rag(rainy_weather)

        assert "rainy" in context.lower()

    def test_context_includes_mom_tip(self, weather_service, perfect_weather):
        """Context should include mom tip."""
        context = weather_service.get_weather_context_for_rag(perfect_weather)

        assert "Mom tip" in context
        assert perfect_weather.mom_tip in context

    def test_context_includes_high_uv_warning(self, weather_service, hot_weather):
        """Context should warn about high UV."""
        context = weather_service.get_weather_context_for_rag(hot_weather)

        assert "UV" in context
        assert "high" in context.lower()

    def test_context_includes_rain_probability(self, weather_service, rainy_weather):
        """Context should include high rain probability."""
        context = weather_service.get_weather_context_for_rag(rainy_weather)

        assert "80%" in context or "rain" in context.lower()

    def test_context_includes_suggestions(self, weather_service, hot_weather):
        """Context should include activity suggestions."""
        context = weather_service.get_weather_context_for_rag(hot_weather)

        assert "Consider recommending" in context


# ============================================================
# CACHE BEHAVIOR TESTS
# ============================================================

class TestCacheBehavior:
    """Test weather service caching."""

    def test_cache_initially_invalid(self, weather_service):
        """Cache should be invalid initially."""
        assert not weather_service._is_cache_valid(38.8462, -77.3064)

    def test_cache_valid_after_set(self, weather_service, perfect_weather):
        """Cache should be valid after setting data."""
        weather_service._cache = perfect_weather
        weather_service._cache_time = time.time()
        weather_service._cache_lat = 38.8462
        weather_service._cache_lon = -77.3064

        assert weather_service._is_cache_valid(38.8462, -77.3064)

    def test_cache_invalid_after_expiry(self, weather_service, perfect_weather):
        """Cache should be invalid after expiry."""
        weather_service._cache = perfect_weather
        weather_service._cache_time = time.time() - 3600  # 1 hour ago (expired)
        weather_service._cache_lat = 38.8462
        weather_service._cache_lon = -77.3064

        assert not weather_service._is_cache_valid(38.8462, -77.3064)

    def test_cache_invalid_for_different_location(self, weather_service, perfect_weather):
        """Cache should be invalid for different location."""
        weather_service._cache = perfect_weather
        weather_service._cache_time = time.time()
        weather_service._cache_lat = 38.8462
        weather_service._cache_lon = -77.3064

        # Different location (more than ~1 mile away)
        assert not weather_service._is_cache_valid(38.9, -77.4)


# ============================================================
# SINGLETON TESTS
# ============================================================

class TestSingleton:
    """Test weather service singleton behavior."""

    def test_get_weather_service_returns_same_instance(self):
        """get_weather_service should return the same instance."""
        service1 = get_weather_service()
        service2 = get_weather_service()

        assert service1 is service2


# ============================================================
# WEATHER CONDITION ENUM TESTS
# ============================================================

class TestWeatherConditionEnum:
    """Test WeatherCondition enum."""

    def test_all_conditions_exist(self):
        """All expected conditions should exist."""
        conditions = [
            WeatherCondition.SUNNY,
            WeatherCondition.PARTLY_CLOUDY,
            WeatherCondition.CLOUDY,
            WeatherCondition.RAINY,
            WeatherCondition.STORMY,
            WeatherCondition.SNOWY,
            WeatherCondition.FOGGY
        ]
        assert len(conditions) == 7

    def test_condition_values_are_strings(self):
        """Condition values should be strings."""
        assert WeatherCondition.SUNNY.value == "sunny"
        assert WeatherCondition.PARTLY_CLOUDY.value == "partly_cloudy"
        assert WeatherCondition.RAINY.value == "rainy"


# ============================================================
# RUN TESTS
# ============================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
