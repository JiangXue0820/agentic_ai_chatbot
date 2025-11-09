"""
Weather Tool Adapter
Provides current, forecast, and historical weather information using Open-Meteo API.
"""
import requests
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from app.utils.config import settings


class WeatherAdapter:
    """
    Weather information retrieval tool.
    
    Supports current, forecast (up to 16 days), and historical (up to 92 days) weather.
    Returns simple temperature, humidity, and condition information.
    """
    
    # Weather query range limits (days)
    MAX_FORECAST_DAYS = 16
    MAX_HISTORICAL_DAYS = 92
    TIMEOUT = 10
    
    # Tool metadata for ToolRegistry
    description = "Get weather information for a location - current, forecast, or historical"
    
    parameters = {
        "type": "object",
        "properties": {
            "location": {
                "type": "string",
                "description": "City name (e.g., 'Singapore', 'Tokyo', 'New York')",
                "required": False
            },
            "city": {
                "type": "string",
                "description": "City name (alias for 'location')",
                "required": False
            },
            "lat": {
                "type": "number",
                "description": "Latitude coordinate",
                "required": False
            },
            "lon": {
                "type": "number",
                "description": "Longitude coordinate",
                "required": False
            },
            "date": {
                "type": "string",
                "description": "Date string like 'today', 'tomorrow', 'yesterday', or YYYY-MM-DD",
                "required": False
            },
            "days_offset": {
                "type": "integer",
                "description": "Days from today (positive=future, negative=past)",
                "required": False
            }
        },
        "required": []
    }
    
    def run(self, **kwargs) -> Dict[str, Any]:
        """
        Unified entry point for the tool.
        
        Returns:
            Dict with:
                - temperature: Temperature in Celsius
                - humidity: Humidity percentage
                - condition: Weather condition description
                OR
                - error: Error message if date out of range
        """
        location = kwargs.get("location") or kwargs.get("city")
        lat = kwargs.get("lat")
        lon = kwargs.get("lon")
        date_str = kwargs.get("date")
        days_offset = kwargs.get("days_offset")
        
        # Parse date
        target_date = self._parse_date(date_str, days_offset)
        today = datetime.now().date()
        days_diff = (target_date - today).days
        
        # Check date range and return error if out of range
        if days_diff > self.MAX_FORECAST_DAYS:
            return {
                "error": f"Only support weather forecast up to {self.MAX_FORECAST_DAYS} days in the future. You requested {days_diff} days ahead."
            }
        
        if days_diff < -self.MAX_HISTORICAL_DAYS:
            return {
                "error": f"Only support historical weather up to {self.MAX_HISTORICAL_DAYS} days in the past. You requested {abs(days_diff)} days ago."
            }
        
        # Geocode city to coordinates
        if location and (lat is None or lon is None):
            try:
                lat, lon = self._geocode(location)
            except ValueError as e:
                return {"error": str(e)}
        
        if lat is None or lon is None:
            return {"error": "Location not specified"}
        
        # Get weather based on date
        try:
            if days_diff == 0:
                return self._get_current(lat, lon, location)
            elif days_diff > 0:
                return self._get_forecast(lat, lon, location, target_date)
            else:
                return self._get_historical(lat, lon, location, target_date)
        except Exception as e:
            return {"error": f"Failed to fetch weather data: {str(e)}"}
    
    def _parse_date(self, date_str: Optional[str], days_offset: Optional[int]) -> datetime.date:
        """Parse date from string or offset."""
        today = datetime.now().date()
        
        if days_offset is not None:
            return today + timedelta(days=days_offset)
        
        if not date_str:
            return today
        
        date_lower = date_str.lower().strip()
        if date_lower in ["today", "now"]:
            return today
        elif date_lower == "tomorrow":
            return today + timedelta(days=1)
        elif date_lower == "yesterday":
            return today - timedelta(days=1)
        
        # Try YYYY-MM-DD format
        try:
            return datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            return today
    
    def _geocode(self, city: str) -> tuple[float, float]:
        """Convert city name to coordinates."""
        g = requests.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": city, "count": 1},
            timeout=self.TIMEOUT
        ).json()
        
        if not g.get("results"):
            raise ValueError(f"City '{city}' not found")
        
        return g["results"][0]["latitude"], g["results"][0]["longitude"]
    
    def _get_current(self, lat: float, lon: float, location: Optional[str]) -> dict:
        """Get current weather."""
        r = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": lat,
                "longitude": lon,
                "current_weather": True,
                "hourly": "relativehumidity_2m",
            },
            timeout=self.TIMEOUT
        ).json()
        
        cur = r.get("current_weather", {})
        humidity = None
        try:
            humidity = r["hourly"]["relativehumidity_2m"][0]
        except Exception:
            pass
        
        return {
            "temperature": cur.get("temperature"),
            "humidity": humidity,
            "condition": self._decode_weather_code(cur.get("weathercode")),
            "location": location or f"({lat}, {lon})",
            "date": "today"
        }
    
    def _get_forecast(self, lat: float, lon: float, location: Optional[str], date: datetime.date) -> dict:
        """Get weather forecast."""
        r = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": lat,
                "longitude": lon,
                "daily": "temperature_2m_max,temperature_2m_min,weathercode",
                "hourly": "relativehumidity_2m",
            },
            timeout=self.TIMEOUT
        ).json()
        
        daily = r.get("daily", {})
        dates = daily.get("time", [])
        date_str = date.strftime("%Y-%m-%d")
        
        if date_str not in dates:
            return {"error": f"Forecast for {date_str} not available"}
        
        idx = dates.index(date_str)
        
        # Get average humidity for that day (rough estimate)
        humidity = None
        try:
            hourly_humidity = r.get("hourly", {}).get("relativehumidity_2m", [])
            if hourly_humidity and len(hourly_humidity) > idx*24:
                day_humidity = hourly_humidity[idx*24:min((idx+1)*24, len(hourly_humidity))]
                if day_humidity:
                    humidity = sum(day_humidity) // len(day_humidity)
        except Exception:
            pass
        
        temp_max = daily["temperature_2m_max"][idx]
        temp_min = daily["temperature_2m_min"][idx]
        
        return {
            "temperature": f"{temp_min}~{temp_max}",  # Range for forecast
            "humidity": humidity,
            "condition": self._decode_weather_code(daily["weathercode"][idx]),
            "location": location or f"({lat}, {lon})",
            "date": date_str
        }
    
    def _get_historical(self, lat: float, lon: float, location: Optional[str], date: datetime.date) -> dict:
        """Get historical weather."""
        date_str = date.strftime("%Y-%m-%d")
        
        r = requests.get(
            "https://archive-api.open-meteo.com/v1/archive",
            params={
                "latitude": lat,
                "longitude": lon,
                "start_date": date_str,
                "end_date": date_str,
                "daily": "temperature_2m_max,temperature_2m_min,weathercode",
            },
            timeout=self.TIMEOUT
        ).json()
        
        daily = r.get("daily", {})
        
        if not daily or not daily.get("time"):
            return {"error": f"Historical data for {date_str} not available"}
        
        temp_max = daily["temperature_2m_max"][0]
        temp_min = daily["temperature_2m_min"][0]
        
        return {
            "temperature": f"{temp_min}~{temp_max}",
            "humidity": None,  # Historical API doesn't provide humidity easily
            "condition": self._decode_weather_code(daily["weathercode"][0]),
            "location": location or f"({lat}, {lon})",
            "date": date_str
        }
    
    def _decode_weather_code(self, code: Optional[int]) -> str:
        """Decode WMO weather code to description."""
        if code is None:
            return "Unknown"
        
        codes = {
            0: "Clear", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
            45: "Fog", 48: "Fog", 51: "Drizzle", 53: "Drizzle", 55: "Drizzle",
            61: "Rain", 63: "Rain", 65: "Heavy rain",
            71: "Snow", 73: "Snow", 75: "Heavy snow", 77: "Snow",
            80: "Rain showers", 81: "Rain showers", 82: "Heavy rain showers",
            85: "Snow showers", 86: "Snow showers",
            95: "Thunderstorm", 96: "Thunderstorm", 99: "Thunderstorm"
        }
        
        return codes.get(code, f"Code {code}")
    