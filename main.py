from datetime import datetime, timedelta, timezone
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
import requests
import gspread
import uvicorn
import os
import logging
import json
import base64
from typing import Optional
import script_exceptions as excp

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

load_dotenv()

app = FastAPI()


class VlessCreation:
    def __init__(
        self,
        credentials_file_path: str = "credentials.json",
        google_sheet_id: Optional[str] = None,
        mac_column: int = 5,
        starting_row: int = 20,
        remna_base_url: Optional[str] = None,
        remna_token: Optional[str] = None,
        days_to_add: Optional[int] = None,
    ) -> None:
        self.starting_row = starting_row
        self.mac_column = mac_column
        self.remna_base_url = remna_base_url or os.getenv("REMNA_BASE_URL")
        self.remna_token = remna_token or os.getenv("REMNA_TOKEN")
        self.remna_headers = {"Authorization": self.remna_token}
        self.days_to_add = days_to_add or int(os.getenv("DAYS_TO_ADD", 365))

        self._validate_configuration(
            google_sheet_id,
            remna_base_url,
            remna_token,
        )

        self._initialize_google_sheets(
            credentials_file_path,
            google_sheet_id,
        )

    def _validate_configuration(
        self,
        google_sheet_id: Optional[str],
        remna_base_url: Optional[str],
        remna_token: Optional[str],
    ) -> None:
        """Validate required configuration parameters"""
        missing_configs = []

        if not (google_sheet_id or os.getenv("GOOGLE_SHEET_ID")):
            missing_configs.append("GOOGLE_SHEET_ID")
        if not (remna_base_url or os.getenv("REMNA_BASE_URL")):
            missing_configs.append("REMNA_BASE_URL")
        if not (remna_token or os.getenv("REMNA_TOKEN")):
            missing_configs.append("REMNA_TOKEN")
        if not os.getenv("GOOGLE_SHEET_PAGE"):
            missing_configs.append("GOOGLE_SHEET_PAGE")
        
        # Check for Google credentials (either file or environment variable)
        if not os.path.exists("credentials.json") and not os.getenv("GOOGLE_CREDENTIALS"):
            missing_configs.append("GOOGLE_CREDENTIALS (or credentials.json file)")

        if missing_configs:
            raise excp.ConfigurationError(
                f"Missing required configuration: {', '.join(missing_configs)}",
            )

    def _initialize_google_sheets(
        self,
        credentials_file_path: str,
        google_sheet_id: Optional[str],
    ) -> None:
        """Initialize Google Sheets connection"""
        try:
            # Try to get credentials from environment variable first
            google_credentials_env = os.getenv("GOOGLE_CREDENTIALS")
            
            if google_credentials_env:
                # Decode base64 credentials from environment variable
                try:
                    credentials_json = base64.b64decode(google_credentials_env).decode('utf-8')
                    credentials_dict = json.loads(credentials_json)
                    google_service = gspread.service_account_from_dict(credentials_dict)
                    logger.info(
                        "Google Sheets service initialized from environment variable",
                    )
                except Exception as e:
                    logger.error(
                        f"Failed to decode Google credentials from environment: {e}",
                    )
                    raise excp.CredentialsError(
                        f"Failed to decode Google credentials from environment: {e}",
                    )
            else:
                # Fall back to file-based credentials
                google_service = gspread.service_account(
                    filename=credentials_file_path,
                )
                logger.info(
                    "Google Sheets service initialized from file",
                )
        except FileNotFoundError:
            logger.error(
                f"Credentials file '{credentials_file_path}' not found",
            )
            raise excp.CredentialsError(
                f"Credentials file '{credentials_file_path}' not found",
            )
        except Exception as e:
            logger.error(
                f"Failed to initialize Google Sheets service: {e}",
            )
            raise excp.CredentialsError(
                f"Failed to initialize Google Sheets service: {e}",
            )

        try:
            sheet_id = google_sheet_id or os.getenv("GOOGLE_SHEET_ID")
            google_spreadsheet = google_service.open_by_url(
                f"https://docs.google.com/spreadsheets/d/{sheet_id}",
            )
            self.google_page = google_spreadsheet.worksheet(
                os.getenv("GOOGLE_SHEET_PAGE"),
            )
            self.mac_col_values = self.google_page.col_values(self.mac_column)
            logger.info(
                "Google Sheet accessed successfully",
            )
        except gspread.exceptions.SpreadsheetNotFound:
            logger.error(
                f"Google Sheet with ID '{sheet_id}' not found",
            )
            raise excp.GoogleSheetError(
                f"Google Sheet with ID '{sheet_id}' not found",
            )
        except gspread.exceptions.WorksheetNotFound:
            page_name = os.getenv("GOOGLE_SHEET_PAGE")
            logger.error(
                f"Worksheet '{page_name}' not found",
            )
            raise excp.GoogleSheetError(
                f"Worksheet '{page_name}' not found",
            )
        except Exception as e:
            logger.error(
                f"Failed to access Google Sheet: {e}",
            )
            raise excp.GoogleSheetError(
                f"Failed to access Google Sheet: {e}",
            )

    def create_payload(
        self,
        mac_address: str,
    ) -> dict:
        """Create payload for user creation"""
        try:
            expire_at = self.create_date(date_from=datetime.now())
            return {
                "username": mac_address,
                "tag": os.getenv("REMNA_TAG"),
                "expireAt": expire_at,
                "status": os.getenv("REMNA_DEFAULT_STATUS"),
                "activeUserInbounds": [os.getenv("REMNA_INBOUND")],
            }
        except Exception as e:
            logger.error(
                f"Failed to create payload for {mac_address}: {e}",
            )
            raise excp.ConfigurationError(
                f"Failed to create payload: {e}",
            )

    def check_mac(
        self,
        mac_address: str,
    ) -> bool:
        """Check if MAC address exists in Google Sheet"""
        if not mac_address:
            raise excp.MacAddressError(
                "MAC address cannot be empty",
            )

        try:
            formatted_input_mac = "".join(e for e in mac_address.lower() if e.isalnum())

            if not formatted_input_mac:
                raise excp.MacAddressError(
                    "Invalid MAC address format",
                )

            for mac in self.mac_col_values[self.starting_row:]:
                if not mac:
                    continue
                formatted_mac = "".join(e for e in mac.lower() if e.isalnum())
                if formatted_mac == formatted_input_mac:
                    logger.info(
                        f"MAC address {mac_address} found in Google Sheet",
                    )
                    return True

            logger.warning(
                f"MAC address {mac_address} not found in Google Sheet",
            )
            return False
        except Exception as e:
            logger.error(
                f"Error checking MAC address {mac_address}: {e}",
            )
            raise excp.GoogleSheetError(
                f"Error checking MAC address: {e}",
            )

    def create_date(self, date_from: datetime = None) -> str:
        """Create ISO formatted date string with additional days"""
        if date_from is None:
            date_from = datetime.now()

        date_plus_one_year = date_from + timedelta(days=self.days_to_add)

        return (
            date_plus_one_year.astimezone(timezone.utc)
            .isoformat(timespec="milliseconds")
            .replace("+00:00", "Z")
        )

    def create_user(
        self,
        mac_address: str,
    ) -> requests.Response:
        """Create user in Remna API"""
        remna_create_user_endpoint = f"{self.remna_base_url}/api/users"

        try:
            payload = self.create_payload(mac_address)
            logger.info(
                f"Creating user for MAC address: {mac_address}",
            )

            response = requests.post(
                remna_create_user_endpoint,
                headers=self.remna_headers,
                json=payload,
                timeout=30,
            )

            if response.status_code == 400:
                logger.info(
                    f"User {mac_address} already exists",
                )
                return response

            response.raise_for_status()
            logger.info(
                f"User created successfully for MAC address: {mac_address}",
            )
            return response

        except requests.exceptions.Timeout:
            logger.error(
                f"Timeout creating user for {mac_address}",
            )
            raise excp.RemnaApiError(
                "Request timeout while creating user",
                "create_user",
            )
        except requests.exceptions.ConnectionError:
            logger.error(
                f"Connection error creating user for {mac_address}",
            )
            raise excp.RemnaApiError(
                "Connection error while creating user",
                "create_user",
            )
        except requests.exceptions.HTTPError as e:
            logger.error(
                f"HTTP error creating user for {mac_address}: {e}",
            )
            raise excp.RemnaApiError(
                f"HTTP error while creating user: {e}",
                "create_user",
            )
        except Exception as e:
            logger.error(
                f"Unexpected error creating user for {mac_address}: {e}",
            )
            raise excp.RemnaApiError(
                f"Unexpected error while creating user: {e}",
                "create_user",
            )

    def get_vless_link(
        self,
        mac_address: str,
    ) -> Optional[str]:
        """Get VLESS link for user"""
        remna_get_subscription_endpoint = (
            f"{self.remna_base_url}/api/subscriptions/by-username/{mac_address}"
        )

        try:
            logger.info(
                f"Retrieving VLESS link for MAC address: {mac_address}",
            )

            response = requests.get(
                remna_get_subscription_endpoint,
                headers=self.remna_headers,
                timeout=30,
            )
            response.raise_for_status()

            response_data = response.json()
            links = response_data.get("response", {}).get("links")

            if links and isinstance(links, list) and len(links) > 0:
                logger.info(
                    f"VLESS link retrieved successfully for {mac_address}",
                )
                return links[0]

            logger.warning(
                f"No VLESS links found for {mac_address}",
            )
            return None

        except requests.exceptions.Timeout:
            logger.error(
                f"Timeout retrieving VLESS link for {mac_address}",
            )
            raise excp.RemnaApiError(
                "Request timeout while retrieving VLESS link",
                "get_vless",
            )
        except requests.exceptions.ConnectionError:
            logger.error(
                f"Connection error retrieving VLESS link for {mac_address}",
            )
            raise excp.RemnaApiError(
                "Connection error while retrieving VLESS link",
                "get_vless",
            )
        except requests.exceptions.HTTPError as e:
            logger.error(
                f"HTTP error retrieving VLESS link for {mac_address}: {e}",
            )
            raise excp.RemnaApiError(
                f"HTTP error while retrieving VLESS link: {e}",
                "get_vless",
            )
        except requests.exceptions.JSONDecodeError:
            logger.error(
                f"Invalid JSON response when retrieving VLESS link for {mac_address}",
            )
            raise excp.RemnaApiError(
                "Invalid JSON response while retrieving VLESS link",
                "get_vless",
            )
        except Exception as e:
            logger.error(
                f"Unexpected error retrieving VLESS link for {mac_address}: {e}",
            )
            raise excp.RemnaApiError(
                f"Unexpected error while retrieving VLESS link: {e}",
                "get_vless",
            )


@app.exception_handler(excp.VlessCreationException)
async def mac_checker_exception_handler(
    request: Request,
    exc: excp.VlessCreationException,
):
    """Handle VlessCreation exceptions"""
    logger.error(
        f"VlessCreation error: {exc.message}",
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.message,
            "error_code": exc.error_code.value,
            "timestamp": datetime.now().isoformat(),
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(
    request: Request,
    exc: Exception,
):
    """Handle unexpected exceptions"""
    logger.error(
        f"Unexpected error: {exc}",
        exc_info=True,
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "error_code": "INTERNAL_SERVER_ERROR",
            "timestamp": datetime.now().isoformat(),
        },
    )


@app.post("/vless")
async def vless(
    request: Request,
):
    """Check MAC address and return VLESS link"""
    try:
        data = await request.json()
        mac_address = data.get("mac_address")

        if not mac_address:
            raise excp.MacAddressError(
                "MAC address is required",
            )

        logger.info(
            f"Processing request for MAC address: {mac_address}",
        )

        mac_checker = VlessCreation()

        if not mac_checker.check_mac(mac_address):
            raise excp.MacAddressError(
                "MAC address not found in Google Sheet",
                not_found=True,
            )

        create_user_response = mac_checker.create_user(mac_address)

        if (
            create_user_response.status_code == 400
            and "User username already exists" in create_user_response.text
        ):
            logger.info(
                f"User {mac_address} already exists, proceeding to retrieve VLESS link",
            )
        elif create_user_response.status_code not in [200, 201]:
            raise excp.RemnaApiError(
                f"Failed to create user. Status: {create_user_response.status_code}",
                "create_user",
            )

        vless_link = mac_checker.get_vless_link(mac_address)
        if not vless_link:
            raise excp.RemnaApiError(
                "No VLESS link available for user",
                "get_vless",
            )

        logger.info(
            f"Successfully processed request for MAC address: {mac_address}",
        )
        return vless_link

    except excp.VlessCreationException:
        raise
    except Exception as e:
        logger.error(
            f"Unexpected error in vless endpoint: {e}",
            exc_info=True,
        )
        raise excp.VlessCreationException(
            "Internal server error occurred",
            excp.ErrorCode.REMNA_API_ERROR,
            500,
        )


@app.post("/tailscale")
async def tailscale(
    request: Request,
):
    """Check MAC address and return Tailscale key"""
    try:
        data = await request.json()
        mac_address = data.get("mac_address")

        if not mac_address:
            raise excp.MacAddressError(
                "MAC address is required",
            )

        logger.info(
            f"Processing Tailscale request for MAC address: {mac_address}",
        )

        mac_checker = VlessCreation()

        if not mac_checker.check_mac(mac_address):
            raise excp.MacAddressError(
                "MAC address not found in Google Sheet",
                not_found=True,
            )

        # Validate Tailscale server availability
        try:
            logger.info(
                f"Checking Tailscale server availability for MAC address: {mac_address}",
            )
            
            # Check connectivity to Tailscale server using socket (ping-like)
            import socket
            
            # Try to connect to the server on port 443 (HTTPS)
            tailscale_base_url = os.getenv("TAILSCALE_BASE_URL")
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10)
            result = sock.connect_ex((tailscale_base_url, 443))
            sock.close()
            
            if result != 0:
                raise ConnectionError("Server is not reachable")
            
            logger.info(
                f"Tailscale server is available for MAC address: {mac_address}",
            )
            
        except socket.timeout:
            logger.error(
                f"Timeout checking Tailscale server for {mac_address}",
            )
            raise excp.TailscaleServerError(
                "Tailscale server timeout",
                "tailscale_check",
            )
        except ConnectionError as e:
            logger.error(
                f"Connection error checking Tailscale server for {mac_address}: {e}",
            )
            raise excp.TailscaleServerError(
                "Tailscale server connection error",
                "tailscale_check",
            )
        except Exception as e:
            logger.error(
                f"Unexpected error checking Tailscale server for {mac_address}: {e}",
            )
            raise excp.TailscaleServerError(
                f"Unexpected error checking Tailscale server: {e}",
                "tailscale_check",
            )

        # Return the Tailscale command for authorized MAC addresses
        tailscale_server = os.getenv("TAILSCALE_BASE_URL")
        tailscale_auth_key = os.getenv("TAILSCALE_AUTH_KEY")
        
        tailscale_command = f"--login-server=https://{tailscale_server} --authkey {tailscale_auth_key}"

        logger.info(
            f"Successfully processed Tailscale request for MAC address: {mac_address}",
        )
        return tailscale_command

    except excp.VlessCreationException:
        raise
    except Exception as e:
        logger.error(
            f"Unexpected error in tailscale endpoint: {e}",
            exc_info=True,
        )
        raise excp.VlessCreationException(
            "Internal server error occurred",
            excp.ErrorCode.REMNA_API_ERROR,
            500,
        )


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
