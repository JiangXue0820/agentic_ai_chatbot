"""
Weather Tool Adapter
Provides current weather information using Open-Meteo or OpenWeather API.
"""
import requests
import time
from typing import Optional, Dict, Any
from app.utils.config import settings


class WeatherAdapter:
    """
    Weather information retrieval tool.
    
    Supports two backends:
    - Open-Meteo (free, no API key required)
    - OpenWeather (requires API key)
    
    Attributes:
        description: Human-readable description of the tool
        parameters: JSON schema defining the tool's parameters
    """
    
    # Tool metadata for ToolRegistry
    description = "Get current weather information for a location by city name or coordinates"
    
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
            }
        },
        "required": [],
        "note": "Either 'location'/'city' OR 'lat'+'lon' must be provided"
    }
    
    def run(self, **kwargs) -> Dict[str, Any]:
        """
        Unified entry point for the tool (required by ToolRegistry).
        
        Args:
            **kwargs: Flexible keyword arguments that can include:
                - location (str): City name
                - city (str): City name (alternative)
                - lat (float): Latitude
                - lon (float): Longitude
        
        Returns:
            Dict with weather information:
                - temperature (float): Temperature in Celsius
                - humidity (int): Relative humidity percentage
                - condition (str/int): Weather condition description or code
                - source (str): API source used
                - observed_at (str): Timestamp in ISO format
        
        Raises:
            ValueError: If city not found
            RuntimeError: If OpenWeather API key is missing when required
        """
        # Support both 'location' and 'city' parameter names
        location = kwargs.get("location") or kwargs.get("city")
        lat = kwargs.get("lat")
        lon = kwargs.get("lon")
        
        return self.current(city=location, lat=lat, lon=lon)
    
    def current(self, city: Optional[str] = None, lat: Optional[float] = None, lon: Optional[float] = None) -> dict:
        """
        Get current weather conditions.
        
        Args:
            city: City name for location lookup
            lat: Latitude coordinate
            lon: Longitude coordinate
        
        Returns:
            Dictionary containing weather data:
                - temperature: Temperature in Celsius
                - humidity: Relative humidity (%)
                - condition: Weather condition code or description
                - source: API provider name
                - observed_at: ISO timestamp
        """
        if settings.WEATHER_API == "open-meteo":
            # Use Open-Meteo (free API)
            if city and (lat is None or lon is None):
                # Geocode city name to coordinates
                g = requests.get(
                    "https://geocoding-api.open-meteo.com/v1/search",
                    params={"name": city, "count": 1}
                ).json()
                if not g.get("results"):
                    raise ValueError(f"City '{city}' not found")
                lat = g["results"][0]["latitude"]
                lon = g["results"][0]["longitude"]
            
            assert lat is not None and lon is not None, "Latitude and longitude are required"
            
            # Fetch weather data
            r = requests.get("https://api.open-meteo.com/v1/forecast", params={
                "latitude": lat,
                "longitude": lon,
                "current_weather": True,
                "hourly": "relativehumidity_2m"
            }).json()
            
            cur = r.get("current_weather", {})
            humidity = None
            try:
                humidity = r["hourly"]["relativehumidity_2m"][0]
            except Exception:
                pass
            
            return {
                "temperature": cur.get("temperature"),
                "humidity": humidity,
                "condition": cur.get("weathercode"),
                "source": "open-meteo",
                "observed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            }
        else:
            # Use OpenWeather API
            key = settings.OPENWEATHER_API_KEY
            if not key:
                raise RuntimeError("OPENWEATHER_API_KEY is required but not configured")
            
            if city:
                r = requests.get(
                    "https://api.openweathermap.org/data/2.5/weather",
                    params={"q": city, "appid": key, "units": "metric"}
                ).json()
            else:
                r = requests.get(
                    "https://api.openweathermap.org/data/2.5/weather",
                    params={"lat": lat, "lon": lon, "appid": key, "units": "metric"}
                ).json()
            
            main = r.get("main", {})
            return {
                "temperature": main.get("temp"),
                "humidity": main.get("humidity"),
                "condition": r.get("weather", [{}])[0].get("main"),
                "source": "openweather",
                "observed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            }
