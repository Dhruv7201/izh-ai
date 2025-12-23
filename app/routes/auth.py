from fastapi import APIRouter, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
import json
import logging
import requests

router = APIRouter(prefix="/auth", tags=["auth"])
limiter = Limiter(key_func=get_remote_address)
logger = logging.getLogger(__name__)

# Static tokens for now (Need to replace when actual flow will be implemented with Frontend!)
STATIC_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJkZTg5Yjc5MC00OTM3LTQ4ZDUtOGI4ZC02YWZjNTU5NzU3NjEiLCJlbWFpbCI6InA1QHlvcG1haWwuY29tIiwibW9iaWxlIjpudWxsLCJyb2xlIjoiZ3Vlc3QiLCJpYXQiOjE3NjYzODM5MDUsImV4cCI6MTc2NjM4NDIwNX0.FeuLWIeL8tvYyhx3mQ1IaC2Bk959epQ-8_-NqGx49qs"
STATIC_REFRESH_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJkZTg5Yjc5MC00OTM3LTQ4ZDUtOGI4ZC02YWZjNTU5NzU3NjEiLCJlbWFpbCI6InA1QHlvcG1haWwuY29tIiwibW9iaWxlIjpudWxsLCJyb2xlIjoiZ3Vlc3QiLCJpYXQiOjE3NjY1MjE4MTYsImV4cCI6MTc2NjY5NDYxNn0.P6CGeVSmWzVEDZPF-5df_7LU7zchbHQg8Vc0kWlmccU"

# Backend API URLs
AUTH_API_URL = "http://15.206.232.1:3000/api/v1/auth/getProfiles"
REFRESH_TOKEN_URL = "http://15.206.232.1:3000/api/v1/auth/refresh-token"
SEND_OTP_URL = "http://15.206.232.1:3000/api/v1/auth/send-otp"
OTP_LOGIN_URL = "http://15.206.232.1:3000/api/v1/auth/otp-login"

# Default OTP payloads (from provided examples)
DEFAULT_OTP_PAYLOAD = {
    "login_value": "p5@yopmail.com",
    "type": "email",
    "deviceId": "DEVICE-123456",
    "context": "login",
    "metadata": {"ip": "192.168.1.10", "platform": "android"},
}

DEFAULT_OTP_LOGIN_BASE = {
    "login_value": "p5@yopmail.com",
    "type": "email",
    "deviceId": "DEVICE-123456",
    "deviceType": "Android",
    "deviceModel": "Samsung S21",
    "appVersion": "1.0.9",
    "ipAddress": "192.168.1.20",
    "latitude": 28.6139,
    "longitude": 77.209,
}


@router.get("/getProfiles")
@limiter.limit("60/minute")
async def get_profiles(request: Request):
    """
    Get user profile details from external auth API.
    
    Args:
        request: FastAPI request object (for rate limiting)
        
    Returns:
        User profile details from external API
    """
    try:
        # Static token for now
        token = STATIC_TOKEN
        
        headers = {
            "accept": "*/*",
            "Authorization": f"Bearer {token}"
        }
        
        resp = requests.get(AUTH_API_URL, headers=headers)
        
        if resp.status_code == 200:
            return resp.json()
        else:
            logger.error(f"Auth API returned status {resp.status_code}: {resp.text}")
            raise HTTPException(
                status_code=resp.status_code,
                detail=f"Failed to get user profile: {resp.text}"
            )
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Error calling auth API: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to connect to auth service: {str(e)}")
    except Exception as e:
        logger.error(f"Error getting user profile: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get user profile: {str(e)}")


def call_get_profiles(access_token: str) -> requests.Response:
    """Call upstream getProfiles with the provided access token."""
    headers = {
        "accept": "*/*",
        "Authorization": f"Bearer {access_token}"
    }
    return requests.get(AUTH_API_URL, headers=headers, timeout=10)


def refresh_tokens(refresh_token: str) -> requests.Response:
    """Call upstream refresh-token API with the provided refresh token."""
    payload = {"refresh_token": refresh_token}
    return requests.post(REFRESH_TOKEN_URL, json=payload, timeout=10)


def run_get_profiles_with_refresh():
    """
    Script-friendly helper:
    1) Calls getProfiles with the static access token.
    2) On 401/403, refreshes using the static refresh token and retries once.
    3) If refresh fails, performs OTP login to fetch fresh tokens and retries.
    """
    print("Calling getProfiles with static access token...")
    first = call_get_profiles(STATIC_TOKEN)
    print(f"First call status: {first.status_code}")
    if first.status_code == 200:
        _print_json(first)
        return

    if first.status_code in (401, 403):
        print("Access token expired/unauthorized. Refreshing...")
        refreshed = refresh_tokens(STATIC_REFRESH_TOKEN)
        print(f"Refresh status: {refreshed.status_code}")
        if refreshed.status_code == 200:
            data = refreshed.json().get("data", {})
            access_token = data.get("accessToken")
            if access_token:
                print("Retrying getProfiles with refreshed access token...")
                second = call_get_profiles(access_token)
                print(f"Second call status: {second.status_code}")
                _print_json(second)
                return
            print("No accessToken in refresh response:", refreshed.text)
        else:
            print("Refresh failed:", refreshed.text)

        # Fallback to OTP flow to get fresh tokens
        print("Attempting OTP flow to obtain new tokens...")
        tokens = perform_otp_login_flow()
        if tokens and tokens.get("accessToken"):
            third = call_get_profiles(tokens["accessToken"])
            print(f"Third call status: {third.status_code}")
            _print_json(third)
        else:
            print("OTP flow failed; could not fetch access token.")
    else:
        print("Unexpected status:", first.status_code, first.text)


def perform_otp_login_flow():
    """
    Runs send-otp then otp-login using returned otp + otp_verify_token.
    Returns a dict with accessToken/refreshToken on success, else {}.
    """
    try:
        print("Sending OTP...")
        send_resp = requests.post(SEND_OTP_URL, json=DEFAULT_OTP_PAYLOAD, timeout=10)
        print(f"send-otp status: {send_resp.status_code}")
        send_json = {}
        try:
            send_json = send_resp.json()
        except Exception:
            pass
        if send_resp.status_code not in (200, 201):
            print("send-otp failed:", send_resp.text)
            return {}
        send_data = send_json.get("data", {}) if isinstance(send_json, dict) else {}
        otp = send_data.get("otp")
        otp_verify_token = send_data.get("otp_verify_token")
        if not otp or not otp_verify_token:
            print("Missing otp or otp_verify_token in send-otp response:", send_resp.text)
            return {}

        login_payload = DEFAULT_OTP_LOGIN_BASE.copy()
        login_payload.update({
            "otp": otp,
            "otp_verify_token": otp_verify_token,
        })

        print("Completing OTP login...")
        login_resp = requests.post(OTP_LOGIN_URL, json=login_payload, timeout=10)
        print(f"otp-login status: {login_resp.status_code}")
        if login_resp.status_code not in (200, 201):
            print("otp-login failed:", login_resp.text)
            return {}
        login_json = {}
        try:
            login_json = login_resp.json()
        except Exception:
            pass
        tokens = login_json.get("data", {}).get("tokens", {}) if isinstance(login_json, dict) else {}
        if not tokens.get("accessToken"):
            print("No access token in otp-login response:", login_resp.text)
            return {}
        return tokens
    except Exception as exc:
        print("OTP flow error:", exc)
        return {}


def _print_json(response: requests.Response):
    """Safely print JSON body if available, else raw text."""
    try:
        data = response.json()
        print(json.dumps(data, indent=2))
    except Exception:
        print(response.text)


if __name__ == "__main__":
    # Run standalone when executed directly (uv run app/routes/auth.py)
    run_get_profiles_with_refresh()
