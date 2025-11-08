# Environment Setup Guide

## Creating .env file

Please create a `.env` file in the project root directory with the following content:

```env
API_TOKEN=changeme
CORS_ALLOW_ORIGINS=["*"]
# Weather
WEATHER_API=open-meteo
OPENWEATHER_API_KEY=
# Gmail
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
# Storage
SQLITE_PATH=./mvp.db
VECTOR_BACKEND=chroma
```

## Configuration Options

### API_TOKEN
- Default: `changeme`
- Description: Bearer token for API authentication
- Production: Change to a secure random string

### CORS_ALLOW_ORIGINS
- Default: `["*"]`
- Description: List of allowed CORS origins
- Production: Restrict to specific domains, e.g., `["https://yourdomain.com"]`

### Weather API
- **WEATHER_API**: Choose between `open-meteo` (default) or `openweather`
- **OPENWEATHER_API_KEY**: Required if using OpenWeather API

### Gmail Integration
- **GOOGLE_CLIENT_ID**: Google OAuth 2.0 Client ID
- **GOOGLE_CLIENT_SECRET**: Google OAuth 2.0 Client Secret
- Note: Currently using mock data; configure these for real Gmail integration

### Storage
- **SQLITE_PATH**: Path to SQLite database file (default: `./mvp.db`)
- **VECTOR_BACKEND**: Vector store backend (`chroma` or fallback to hash-based)

## Quick Start

1. Copy this configuration to `.env`
2. Modify values as needed
3. Keep `.env` file secure and never commit it to version control

