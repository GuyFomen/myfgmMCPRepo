# ==== SECTION 1: Imports & setup ===================
import httpx
from env_canada import ECWeather, ECAlerts
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("myfgmweather_ca")

# ==== SECTION 2: city coordinate ===================
async def get_coordinates(city: str) -> tuple[float, float] |None:
    """
    convert a Canadian City name into Coordinates using geocoding.
    """
    city = city.lower()
    url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}&country=CA&count=1&language=en"
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, timeout=10.0)
            data = response.json()
            if data.get("results"):
                result = data.get("results")[0]
                return (result["latitude"], result["longitude"])
            return None
        except Exception:
            return None

# ==== SECTION 2: Tools =============================
@mcp.tool()
async def get_canadian_weather(city: str) -> str:
    """
    Get Current weather for any city.
    Args:
        city: Any Canadian city name (e.g Sashatoon, Ottawa, Fredericton)
    """

    coords = await get_coordinates(city)
    if not coords:
        return f"Could not find coordinates for '{city}'. Please check the city name."
    try:
        ec = ECWeather(coordinates=coords, language="english")
        await ec.update()

        conditions = ec.conditions
        forecasts = ec.daily_forecasts

        # Format current conditions
        result = f"""
        Current Conditions - {city.title()}
        -------------------------------------
        Temperature: {conditions.get('temperature', {}).get('value', 'NA')}°C
        Feels Like: {conditions.get('wind_chill', {}).get('value', 'NA')}°C
        Humidity: {conditions.get('humidity', {}).get('value', 'NA')}%
        Wind: {conditions.get('wind_speed', {}).get('value', 'NA')} km/h {conditions.get('wind_dir', {}).get('value', 'NA')}
        Visibility: {conditions.get('visibility', {}).get('value', 'NA')}km
        Pressure: {conditions.get('pressure', {}).get('value', 'NA')} kpa
        Condition: {conditions.get('condition', {}).get('value', 'NA')}°C
        """
        # Format next 3 days forecast
        result +="\n7-Day Forecast:\n" + "-" * 37 + "\n"
        for day in forecasts[:7]:
            result += f"{day.get('period', 'N/A')}:{day.get('text_summary', 'N/A')}| High: {day.get('temperature', 'N/A')}°C\n"
        return result
    
    except Exception as e:
        return f"Unable to fetch weather for {city}: {str(e)}"

@mcp.tool()
async def get_canadian_alerts(city: str) -> str:
    """
    Get active weather alerts for a Canadian city
    Args:
        city: City name (e.g. Ottawa, toronto, vancouver)
    """
    coords = await get_coordinates(city)
    if not coords:
        return f"Could not find coordinates for '{city}'. Please check the city name."
    
    try:
        ec_alerts = ECAlerts(coordinates=coords)
        await ec_alerts.update()

        alerts = ec_alerts.alerts

        if not any(alerts.get(k, {}).get("value") for k in ["warnings", "watches", "advisories", "statements"]):
            return f"No active alerts for {city.title()}."
        
        result = f"Active Alerts - {city.title()}\n" + "-" * 37 + "\n"
        for category in ["warnings", "watches", "advisories", "statements"]:
            items = alerts.get(category, {}).get("value", [])
            for item in items:
                result +=f"""
                [{category.upper()}] {item.get('title',{}).get('value', 'N/A')}
                {item.get('text', {}).get('value', 'N/A')[:10]}
                """
        return result
    except Exception as e:
        return f"Unable to fetch alerts for {city}: {str(e)}"

# == SECTION 3: Run the server ============================
def main():
    mcp.run(transport="stdio")

if __name__ == "__main__":
    main()