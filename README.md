# Router API

A FastAPI-based service that validates MAC addresses against a Google Sheets database and provides VLESS proxy links for authorized devices.

## Overview

This API serves as a bridge between device authentication and proxy service provisioning. It:

1. Receives MAC address requests
2. Validates them against a Google Sheets database
3. Creates users in the Remna proxy service (if not already existing)
4. Returns VLESS proxy links for authorized devices

## Features

- **MAC Address Validation**: Checks incoming MAC addresses against a Google Sheets database
- **Automatic User Creation**: Creates users in Remna proxy service for new MAC addresses
- **VLESS Link Generation**: Provides VLESS proxy links for authorized devices
- **Error Handling**: Comprehensive error handling with detailed logging
- **RESTful API**: Clean FastAPI-based REST endpoints

## Prerequisites

- Python 3.11 or higher
- Google Sheets API credentials
- Remna proxy service access
- Google Sheets database with MAC addresses

## Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd router-api
   ```

2. **Install dependencies**
   ```bash
   uv sync
   ```

3. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. **Set up Google Sheets credentials**
   - Create a Google Cloud Project
   - Enable Google Sheets API
   - Create a service account
   - Download the credentials JSON file
   - Place it in the project root as `credentials.json`

## Configuration

### Environment Variables

Create a `.env` file with the following variables:

```bash
# Google Sheets Configuration
GOOGLE_SHEET_ID=your_google_sheet_id
GOOGLE_SHEET_PAGE=Sheet1

# Remna API Configuration
REMNA_BASE_URL=https://your-remna-instance.com
REMNA_TOKEN=your_remna_api_token
REMNA_TAG=default_tag
REMNA_DEFAULT_STATUS=active
REMNA_INBOUND=default_inbound

# Application Configuration
DAYS_TO_ADD=365
```

### Google Sheets Setup

1. Create a Google Sheet with MAC addresses in a specific column
2. Share the sheet with your service account email
3. Note the sheet ID from the URL
4. Configure the column number and starting row in the code

### Remna API Setup

1. Obtain your Remna API base URL
2. Generate an API token with appropriate permissions
3. Configure the default tag, status, and inbound settings

## Usage

### Running the API

```bash
# Development
uv run main.py

# Production with uvicorn
uv run uvicorn main:app --host 0.0.0.0 --port 8000
```

### API Endpoints

#### POST `/check`

Validates a MAC address and returns a VLESS link.

**Request Body:**
```json
{
  "mac_address": "00:11:22:33:44:55"
}
```

**Response:**
- **Success**: Returns the VLESS link as a string
- **Error**: Returns error details with appropriate HTTP status codes

**Example:**
```bash
curl -X POST http://localhost:8000/check \
  -H "Content-Type: application/json" \
  -d '{"mac_address": "00:11:22:33:44:55"}'
```

### Error Handling

The API returns structured error responses with the following format:

```json
{
  "error": "Error message",
  "error_code": "ERROR_CODE",
  "timestamp": "2024-01-01T12:00:00.000Z"
}
```

Common error codes:
- `MAC_ADDRESS_NOT_FOUND`: MAC address not found in Google Sheet
- `INVALID_MAC_ADDRESS`: Invalid MAC address format
- `REMNA_API_ERROR`: Remna API communication error
- `GOOGLE_SHEET_ACCESS_ERROR`: Google Sheets access error
- `CONFIGURATION_ERROR`: Missing or invalid configuration

## Development

### Project Structure

```
router-api/
├── main.py                 # Main FastAPI application
├── script_exceptions.py    # Custom exception classes
├── pyproject.toml         # Project dependencies and metadata
├── credentials.json       # Google Sheets API credentials (not in repo)
├── .env                   # Environment variables (not in repo)
└── README.md             # This file
```

### Dependencies

- **FastAPI**: Web framework for building APIs
- **gspread**: Google Sheets API client
- **python-dotenv**: Environment variable management
- **requests**: HTTP client for Remna API calls
- **uvicorn**: ASGI server for running the application

### Logging

The application uses Python's built-in logging module with INFO level by default. Logs include:
- Request processing information
- MAC address validation results
- API call outcomes
- Error details

## Security Considerations

- Store sensitive credentials in environment variables, not in code
- Use HTTPS in production
- Implement rate limiting for production use
- Regularly rotate API tokens
- Monitor API usage and logs

## Troubleshooting

### Common Issues

1. **Credentials file not found**
   - Ensure `credentials.json` is in the project root
   - Verify the file has correct permissions

2. **Google Sheet access denied**
   - Check that the service account has access to the sheet
   - Verify the sheet ID and page name are correct

3. **Remna API errors**
   - Verify the base URL and token are correct
   - Check network connectivity to Remna service

4. **MAC address not found**
   - Ensure the MAC address is in the correct column
   - Check the starting row configuration
   - Verify MAC address format

## GitHub Integration

### GitHub Actions

This project includes a GitHub Actions workflow (`.github/workflows/deploy.yml`) that:

1. **Tests** your code on every push and pull request
2. **Lints** code for style and quality
3. **Builds** a Docker image to ensure it works
4. **Tests** the Docker image to verify deployment readiness

### Running Locally with GitHub Codespaces

You can run this application directly in GitHub Codespaces:

1. **Open in Codespaces**: Click the green "Code" button and select "Open with Codespaces"
2. **Install dependencies**: `uv sync`
3. **Set environment variables**: Create a `.env` file with your configuration
4. **Run the app**: `uv run main.py`

### Environment Variables

For local development or Codespaces, create a `.env` file with:

- `GOOGLE_SHEET_ID`
- `GOOGLE_SHEET_PAGE`
- `REMNA_BASE_URL`
- `REMNA_TOKEN`
- `REMNA_TAG`
- `REMNA_DEFAULT_STATUS`
- `REMNA_INBOUND`
- `DAYS_TO_ADD`

**⚠️ Security Note**: Never commit your `.env` file to the repository. It's already in `.gitignore` to prevent accidental commits.

### Google Sheets Credentials

You have two options for Google Sheets credentials:

#### Option 1: Environment Variable (Recommended for Deployment)
1. **Encode your credentials.json**:
   ```bash
   # Using the helper script (recommended)
   python encode_credentials.py
   
   # Or manually
   base64 -i credentials.json | tr -d '\n'
   ```
2. **Add to environment variables**:
   - Local: Add `GOOGLE_CREDENTIALS=your_encoded_credentials` to `.env`
   - Deployment: Add as `GOOGLE_CREDENTIALS` secret in your platform

#### Option 2: File-based (Local Development)
1. **Place credentials.json** in the project root
2. **The app will automatically detect** and use the file

#### Option 3: Google Cloud IAM (Advanced)
Use Google Cloud IAM instead of service account keys for better security.

## License

[Add your license information here]

## Contributing

[Add contribution guidelines here] 