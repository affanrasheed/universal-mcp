"""
Main MCP server implementation with various tools and API integrations.

This server exposes several tools that leverage free public APIs for:
- Weather information
- Cryptocurrency prices
- News headlines
- Web search queries
- Random jokes
"""
import asyncio
import json
import os
from datetime import datetime
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Optional, Any, Dict, List

import httpx
from mcp.server.fastmcp import FastMCP, Context
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Create the MCP server
mcp = FastMCP("Universal MCP Server")

# ===== Weather API =====
@mcp.tool()
async def get_weather(city: str, country_code: Optional[str] = None) -> str:
    """
    Get current weather information for a city.
    
    Args:
        city: The name of the city
        country_code: Optional ISO 3166 country code (e.g., 'US' for United States)
    
    Returns:
        Weather information in text format
    """
    # Using OpenWeatherMap's free API
    api_key = os.getenv("OPENWEATHER_API_KEY", "")
    if not api_key:
        return "Error: OpenWeatherMap API key not configured. Please set OPENWEATHER_API_KEY environment variable."
    
    query = f"{city},{country_code}" if country_code else city
    url = f"https://api.openweathermap.org/data/2.5/weather?q={query}&appid={api_key}&units=metric"
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()
            
            # Extract relevant information
            weather_desc = data["weather"][0]["description"]
            temp = data["main"]["temp"]
            feels_like = data["main"]["feels_like"]
            humidity = data["main"]["humidity"]
            wind_speed = data["wind"]["speed"]
            
            return f"""Weather in {city}:
- Conditions: {weather_desc}
- Temperature: {temp}°C (feels like {feels_like}°C)
- Humidity: {humidity}%
- Wind Speed: {wind_speed} m/s
"""
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return f"City not found: {city}"
            return f"Error fetching weather data: {str(e)}"
        except Exception as e:
            return f"An unexpected error occurred: {str(e)}"

# ===== Cryptocurrency API =====
@mcp.tool()
async def get_crypto_price(symbol: str) -> str:
    """
    Get the current price of a cryptocurrency.
    
    Args:
        symbol: Cryptocurrency symbol (e.g., BTC, ETH, SOL)
    
    Returns:
        Current price information
    """
    # Using CoinGecko's free API
    symbol = symbol.lower()
    url = f"https://api.coingecko.com/api/v3/simple/price?ids={symbol}&vs_currencies=usd,eur&include_24hr_change=true"
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()
            
            if not data or symbol not in data:
                return f"Cryptocurrency not found: {symbol}. Try using the full name (e.g., 'bitcoin' instead of 'BTC')."
            
            crypto_data = data[symbol]
            usd_price = crypto_data.get("usd", "N/A")
            eur_price = crypto_data.get("eur", "N/A")
            change_24h = crypto_data.get("usd_24h_change", "N/A")
            
            if change_24h != "N/A":
                change_24h = f"{change_24h:.2f}%"
            
            return f"""Current {symbol.upper()} price:
- USD: ${usd_price}
- EUR: €{eur_price}
- 24h Change: {change_24h}
"""
        except Exception as e:
            return f"Error fetching cryptocurrency data: {str(e)}"

# ===== News API =====
@mcp.tool()
async def get_news_headlines(topic: str = "", country: str = "us", count: int = 5) -> str:
    """
    Get top news headlines, optionally filtered by topic.
    
    Args:
        topic: Topic to filter headlines (optional)
        country: Country code (default: 'us')
        count: Number of headlines to return (default: 5, max: 10)
    
    Returns:
        News headlines in text format
    """
    # Using NewsAPI's free tier
    api_key = os.getenv("NEWSAPI_KEY", "")
    if not api_key:
        return "Error: NewsAPI key not configured. Please set NEWSAPI_KEY environment variable."
    
    # Enforce maximum count
    count = min(count, 10)
    
    # Construct URL
    params = {
        "apiKey": api_key,
        "country": country,
        "pageSize": count
    }
    
    if topic:
        params["q"] = topic
    
    url = "https://newsapi.org/v2/top-headlines"
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            if data["status"] != "ok":
                return f"Error: {data.get('message', 'Unknown error')}"
            
            articles = data["articles"]
            if not articles:
                return f"No news found for the given criteria."
            
            result = f"Top {len(articles)} news headlines"
            if topic:
                result += f" about '{topic}'"
            result += ":\n\n"
            
            for i, article in enumerate(articles, 1):
                pub_date = article.get("publishedAt", "").split("T")[0]
                result += f"{i}. {article['title']}\n"
                result += f"   Source: {article.get('source', {}).get('name', 'Unknown')}\n"
                if pub_date:
                    result += f"   Date: {pub_date}\n"
                if article.get("url"):
                    result += f"   URL: {article['url']}\n"
                result += "\n"
            
            return result.strip()
        except Exception as e:
            return f"Error fetching news data: {str(e)}"

# ===== Joke API =====
@mcp.tool()
async def get_random_joke(category: Optional[str] = None) -> str:
    """
    Get a random joke, optionally from a specific category.
    
    Args:
        category: Joke category (optional - 'programming', 'misc', 'dark', 'pun', 'spooky', 'christmas')
    
    Returns:
        A random joke
    """
    url = "https://v2.jokeapi.dev/joke/"
    
    if category:
        url += category
    else:
        url += "Any"
    
    url += "?safe-mode"  # Ensure jokes are SFW
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()
            
            if data.get("error"):
                return f"Error: {data.get('message', 'Unknown error')}"
            
            if data["type"] == "single":
                return data["joke"]
            else:
                return f"{data['setup']}\n\n{data['delivery']}"
        except Exception as e:
            return f"Error fetching joke: {str(e)}"

# ===== Web Search API =====
@mcp.tool()
async def web_search(query: str, count: int = 5) -> str:
    """
    Search the web for information.
    
    Args:
        query: Search query
        count: Number of results to return (default: 5, max: 10)
    
    Returns:
        Search results in text format
    """
    # Using SerpApi's free tier
    api_key = os.getenv("SERPAPI_KEY", "")
    if not api_key:
        return "Error: SerpAPI key not configured. Please set SERPAPI_KEY environment variable."
    
    # Enforce maximum count
    count = min(count, 10)
    
    # Construct URL
    params = {
        "api_key": api_key,
        "q": query,
        "num": count,
        "engine": "google"
    }
    
    url = "https://serpapi.com/search"
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            if "error" in data:
                return f"Error: {data.get('error', 'Unknown error')}"
            
            organic_results = data.get("organic_results", [])
            if not organic_results:
                return "No search results found."
            
            result = f"Search results for '{query}':\n\n"
            
            for i, item in enumerate(organic_results[:count], 1):
                result += f"{i}. {item.get('title', 'No title')}\n"
                if item.get("snippet"):
                    result += f"   {item['snippet']}\n"
                if item.get("link"):
                    result += f"   URL: {item['link']}\n"
                result += "\n"
            
            return result.strip()
        except Exception as e:
            return f"Error performing web search: {str(e)}"

# ===== Dictionary API =====
@mcp.tool()
async def define_word(word: str) -> str:
    """
    Get the definition of a word.
    
    Args:
        word: The word to define
    
    Returns:
        Word definition(s)
    """
    # Using Free Dictionary API
    url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}"
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()
            
            if not data or isinstance(data, dict) and "title" in data:
                return f"No definition found for '{word}'."
            
            result = f"Definitions for '{word}':\n\n"
            
            for entry in data:
                if "meanings" in entry:
                    for meaning in entry["meanings"]:
                        part_of_speech = meaning.get("partOfSpeech", "")
                        result += f"Part of Speech: {part_of_speech}\n"
                        
                        for i, definition in enumerate(meaning.get("definitions", []), 1):
                            result += f"{i}. {definition.get('definition', '')}\n"
                            
                            if definition.get("example"):
                                result += f"   Example: \"{definition['example']}\"\n"
                            
                            result += "\n"
                
                if "phonetics" in entry and entry["phonetics"]:
                    for phonetic in entry["phonetics"]:
                        if phonetic.get("text"):
                            result += f"Pronunciation: {phonetic['text']}\n"
                            break
            
            return result.strip()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return f"No definition found for '{word}'."
            return f"Error fetching definition: {str(e)}"
        except Exception as e:
            return f"An unexpected error occurred: {str(e)}"

# ===== Current Time and Date =====
@mcp.tool()
def get_current_time(timezone: str = "UTC") -> str:
    """
    Get the current time and date.
    
    Args:
        timezone: Timezone (currently only supports 'UTC' or 'local')
    
    Returns:
        Current time and date information
    """
    now = datetime.now()
    utc_now = datetime.utcnow()
    
    if timezone.lower() == "local":
        time_str = now.strftime("%Y-%m-%d %H:%M:%S (Local Time)")
    else:
        time_str = utc_now.strftime("%Y-%m-%d %H:%M:%S (UTC)")
    
    return f"Current time: {time_str}"

# Run the server when executed directly
if __name__ == "__main__":
    mcp.run()