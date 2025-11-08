"""
Quick test for weather forecast and historical query enhancement.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from app.tools.weather import WeatherAdapter
from datetime import datetime, timedelta

print("=" * 70)
print("Weather Enhancement Test")
print("=" * 70)

weather = WeatherAdapter()

# Test cases
test_cases = [
    # Current weather
    {
        "name": "Current weather in Singapore",
        "kwargs": {"location": "Singapore"},
        "expected": "temperature, humidity, condition"
    },
    # Tomorrow
    {
        "name": "Tomorrow weather in Harbin",
        "kwargs": {"location": "Harbin", "days_offset": 1},
        "expected": "forecast with temperature range"
    },
    # In 5 days
    {
        "name": "Weather in Tokyo in 5 days",
        "kwargs": {"location": "Tokyo", "days_offset": 5},
        "expected": "forecast"
    },
    # Yesterday
    {
        "name": "Yesterday weather in London",
        "kwargs": {"location": "London", "days_offset": -1},
        "expected": "historical data"
    },
    # Out of range - future
    {
        "name": "Weather in 20 days (should error)",
        "kwargs": {"location": "Singapore", "days_offset": 20},
        "expected": "error message about 16 days limit"
    },
    # Out of range - past
    {
        "name": "Weather 100 days ago (should error)",
        "kwargs": {"location": "Singapore", "days_offset": -100},
        "expected": "error message about 92 days limit"
    },
    # Invalid city
    {
        "name": "Weather in Atlantis (invalid city)",
        "kwargs": {"location": "Atlantis"},
        "expected": "city not found error"
    }
]

print("\nRunning test cases:\n")
print("-" * 70)

for i, test in enumerate(test_cases, 1):
    print(f"\n{i}. {test['name']}")
    print(f"   Input: {test['kwargs']}")
    print(f"   Expected: {test['expected']}")
    
    try:
        result = weather.run(**test['kwargs'])
        
        # Check if it's an error
        if "error" in result:
            print(f"   ❌ Error: {result['error']}")
        else:
            # Format success response
            temp = result.get('temperature')
            humidity = result.get('humidity')
            condition = result.get('condition')
            location = result.get('location', '')
            date = result.get('date', '')
            
            output = f"   ✅ {location}"
            if date and date != 'today':
                output += f" on {date}"
            output += f": {temp}°C"
            if humidity:
                output += f", {humidity}% humidity"
            output += f", {condition}"
            
            print(output)
    
    except Exception as e:
        print(f"   ❌ Exception: {e}")

print("\n" + "=" * 70)
print("Test Summary")
print("=" * 70)

print("""
Expected Results:
✅ Test 1-4: Should show weather data
❌ Test 5-6: Should show range limit errors
❌ Test 7: Should show city not found error

If all tests behave as expected, the enhancement is working correctly!
""")

print("=" * 70)

