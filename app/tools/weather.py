import requests
import time
from typing import Optional
from app.utils.config import settings

class WeatherAdapter:
    def current(self, city: Optional[str] = None, lat: Optional[float] = None, lon: Optional[float] = None) -> dict:
        if settings.WEATHER_API == "open-meteo":
            if city and (lat is None or lon is None):
                g = requests.get("https://geocoding-api.open-meteo.com/v1/search", params={"name": city, "count": 1}).json()
                if not g.get("results"):
                    raise ValueError("City not found")
                lat = g["results"][0]["latitude"]
                lon = g["results"][0]["longitude"]
            assert lat is not None and lon is not None
            r = requests.get("https://api.open-meteo.com/v1/forecast", params={
                "latitude": lat, "longitude": lon, "current_weather": True, "hourly": "relativehumidity_2m"
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
            key = settings.OPENWEATHER_API_KEY
            if not key:
                raise RuntimeError("OPENWEATHER_API_KEY missing")
            if city:
                r = requests.get("https://api.openweathermap.org/data/2.5/weather", params={"q": city, "appid": key, "units": "metric"}).json()
            else:
                r = requests.get("https://api.openweathermap.org/data/2.5/weather", params={"lat": lat, "lon": lon, "appid": key, "units": "metric"}).json()
            main = r.get("main", {})
            return {
                "temperature": main.get("temp"),
                "humidity": main.get("humidity"),
                "condition": r.get("weather", [{}])[0].get("main"),
                "source": "openweather",
                "observed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            }
