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
# LLM Configuration
LLM_PROVIDER=mock
DEEPSEEK_API_KEY=
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
GEMINI_API_KEY=
GEMINI_MODEL=gemini-pro
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4o-mini
OPENAI_BASE_URL=
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

### LLM Provider Configuration

#### LLM_PROVIDER
- Default: `mock`
- Options: `mock`, `deepseek`, `gemini`, `openai`
- Description: Choose which LLM provider to use for chat and summarization

#### DeepSeek (when LLM_PROVIDER=deepseek)
- **DEEPSEEK_API_KEY**: Your DeepSeek API key
  - Get it from: https://platform.deepseek.com
  - Very affordable pricing, excellent for Chinese and English
- **DEEPSEEK_BASE_URL**: DeepSeek API endpoint (default: `https://api.deepseek.com`)
- **DEEPSEEK_MODEL**: Model name (default: `deepseek-chat`)

#### Google Gemini (when LLM_PROVIDER=gemini)
- **GEMINI_API_KEY**: Your Gemini API key
  - Get it from: https://ai.google.dev
  - Free tier available with generous limits
- **GEMINI_MODEL**: Model name (default: `gemini-pro`)

#### OpenAI (when LLM_PROVIDER=openai)
- **OPENAI_API_KEY**: Your OpenAI API key
  - Get it from: https://platform.openai.com
  - Pay-as-you-go pricing
- **OPENAI_MODEL**: Model name (default: `gpt-4o-mini`)
- **OPENAI_BASE_URL**: Optional custom endpoint (leave empty for default)

#### Getting Started with LLM

**For testing (no cost):**
```env
LLM_PROVIDER=mock
```

**For DeepSeek (recommended - affordable):**
```env
LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=sk-your-actual-key-here
```

**For Gemini (free tier available):**
```env
LLM_PROVIDER=gemini
GEMINI_API_KEY=your-gemini-key-here
```

**For OpenAI:**
```env
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-your-openai-key-here
```

## Quick Start

1. Copy this configuration to `.env`
2. Modify values as needed
3. For LLM: Choose a provider and add the corresponding API key
4. Keep `.env` file secure and never commit it to version control

