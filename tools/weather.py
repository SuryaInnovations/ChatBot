"""
Live Weather tool module.
Retrieves real-time weather information and short-term forecasts for cities worldwide.
Uses wttr.in JSON API with Open-Meteo fallback, requiring zero API keys.
"""

import json
import logging
import urllib.request
import urllib.parse
from typing import Dict, Any

logger = logging.getLogger("chatbot.tools.weather")

def get_live_weather(location: str) -> Dict[str, Any]:
    """
    Retrieves current weather and forecast for a given location or city.
    
    Args:
        location: City or location name, e.g. 'Tokyo', 'London', 'San Francisco'.
        
    Returns:
        Dict with success status, temperature in C and F, condition, humidity, wind, and formatted summary.
    """
    loc_clean = location.strip()
    if not loc_clean:
        return {"success": False, "error": "Location cannot be empty."}

    # Remove common conversational phrases
    clean_city = loc_clean
    for prefix in [
        "what is the weather in", "what's the weather in", "weather in", "weather for",
        "weather of", "how is the weather in", "current weather in", "temperature in",
        "is it raining in", "forecast for", "weather"
    ]:
        if clean_city.lower().startswith(prefix):
            clean_city = clean_city[len(prefix):].strip()
            break
    clean_city = clean_city.strip(" ?.!/\\")
    if not clean_city:
        clean_city = loc_clean

    # 1. Primary Source: wttr.in JSON API
    try:
        encoded_city = urllib.parse.quote(clean_city)
        url = f"https://wttr.in/{encoded_city}?format=j1"
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "curl/7.68.0",
                "Accept": "application/json"
            }
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))
            
            curr = data.get("current_condition", [{}])[0]
            nearest_area = data.get("nearest_area", [{}])[0]
            
            city_name = nearest_area.get("areaName", [{}])[0].get("value", clean_city.title())
            country = nearest_area.get("country", [{}])[0].get("value", "")
            
            temp_c = curr.get("temp_C", "N/A")
            temp_f = curr.get("temp_F", "N/A")
            feels_c = curr.get("FeelsLikeC", temp_c)
            feels_f = curr.get("FeelsLikeF", temp_f)
            condition = curr.get("weatherDesc", [{}])[0].get("value", "Clear").strip()
            humidity = curr.get("humidity", "N/A")
            wind_kmph = curr.get("windspeedKmph", "N/A")
            wind_dir = curr.get("winddir16Point", "")
            uv_index = curr.get("uvIndex", "N/A")
            visibility = curr.get("visibility", "N/A")

            # Extract 2-day forecast if present
            weather_forecast = []
            for day in data.get("weather", [])[:2]:
                date = day.get("date", "")
                max_c = day.get("maxtempC", "")
                min_c = day.get("mintempC", "")
                hourly_desc = day.get("hourly", [{}])[4].get("weatherDesc", [{}])[0].get("value", "Clear") if day.get("hourly") else ""
                weather_forecast.append({
                    "date": date,
                    "max_c": max_c,
                    "min_c": min_c,
                    "condition": hourly_desc
                })

            summary = (
                f"🌤️ **Weather in {city_name}, {country}**:\n"
                f"- **Condition:** {condition}\n"
                f"- **Temperature:** {temp_c}°C ({temp_f}°F) [Feels like: {feels_c}°C / {feels_f}°F]\n"
                f"- **Humidity:** {humidity}%\n"
                f"- **Wind:** {wind_kmph} km/h ({wind_dir})\n"
                f"- **UV Index:** {uv_index} | **Visibility:** {visibility} km"
            )

            return {
                "success": True,
                "city": city_name,
                "country": country,
                "location": f"{city_name}, {country}".strip(", "),
                "celsius": temp_c,
                "condition": condition,
                "temp_c": temp_c,
                "temp_f": temp_f,
                "feels_like_c": feels_c,
                "feels_like_f": feels_f,
                "humidity": humidity,
                "wind_kmph": wind_kmph,
                "wind_dir": wind_dir,
                "forecast": weather_forecast,
                "summary": summary
            }

    except Exception as e:
        logger.warning(f"wttr.in weather fetch failed for '{clean_city}': {e}. Attempting fallback.")

    # 2. Fallback Source: Open-Meteo Geocoding + Weather
    try:
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={urllib.parse.quote(clean_city)}&count=1"
        geo_req = urllib.request.Request(geo_url, headers={"User-Agent": "SPARK-AI-Weather/1.0"})
        with urllib.request.urlopen(geo_req, timeout=4) as g_resp:
            g_data = json.loads(g_resp.read().decode("utf-8"))
            results = g_data.get("results")
            if not results:
                return {
                    "success": False,
                    "error": f"Could not find geographic location for '{clean_city}'."
                }
            lat = results[0]["latitude"]
            lon = results[0]["longitude"]
            city_name = results[0].get("name", clean_city)
            country = results[0].get("country", "")

        meteo_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
        meteo_req = urllib.request.Request(meteo_url, headers={"User-Agent": "SPARK-AI-Weather/1.0"})
        with urllib.request.urlopen(meteo_req, timeout=4) as m_resp:
            m_data = json.loads(m_resp.read().decode("utf-8"))
            cw = m_data.get("current_weather", {})
            temp_c = cw.get("temperature", "N/A")
            temp_f = round(float(temp_c) * 9/5 + 32, 1) if isinstance(temp_c, (int, float)) else "N/A"
            wind_kmph = cw.get("windspeed", "N/A")

            summary = (
                f"🌤️ **Weather in {city_name}, {country}**:\n"
                f"- **Temperature:** {temp_c}°C ({temp_f}°F)\n"
                f"- **Wind Speed:** {wind_kmph} km/h\n"
                f"- **Coordinates:** ({lat}, {lon})"
            )

            return {
                "success": True,
                "location": f"{city_name}, {country}".strip(", "),
                "city": city_name,
                "country": country,
                "temp_c": temp_c,
                "temp_f": temp_f,
                "wind_kmph": wind_kmph,
                "summary": summary
            }

    except Exception as e2:
        logger.error(f"Weather fallback also failed for '{clean_city}': {e2}")
        return {
            "success": False,
            "error": f"Unable to retrieve live weather for '{clean_city}'. Please check your network connection or specify a different city name."
        }
