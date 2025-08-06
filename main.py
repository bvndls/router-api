from datetime import datetime, timedelta, timezone
from fastapi import FastAPI, Request
from dotenv import load_dotenv
import requests
import gspread
import uvicorn
import json
import os

load_dotenv()

app = FastAPI()

gc = gspread.service_account(filename='credentials.json')
ss = gc.open_by_url(f"https://docs.google.com/spreadsheets/d/{os.getenv('GOOGLE_SHEET_ID')}")
sh = ss.worksheet(os.getenv('GOOGLE_SHEET_PAGE'))
values = sh.col_values(5) # service-specific (5 is the column number)

# TODO ERROR HANDLING, get vless link if user is already created
@app.post("/check")
async def check(request: Request):
    data = await request.json()
    mac_address = data.get("mac_address")
    if not mac_address:
        return {"error": "Mac address is required"}
    is_in_sheet = check_google_sheet(mac_address)
    if not is_in_sheet:
        return {"error": "Mac address is not in the google sheet"}
    create_user_response = create_user(mac_address)
    if create_user_response // 100 != 2:
        return {"error": "Failed to create user", "status_code": create_user_response}
    vless_link = get_vless_link(mac_address)
    if not vless_link:
        return {"error": "Failed to get vless link"}
    return vless_link

def check_google_sheet(mac_address):
    for row in values[20:]:
        formatted_row = ''.join(e for e in row.lower() if e.isalnum())
        if formatted_row == mac_address:
            return True
    return False

def create_user(mac_address):
    url = f"https://{os.getenv('BASE_URL')}/api/users"
    headers = {
        "Authorization": f"Bearer {os.getenv('TOKEN')}"
    }
    expire_at = f"{datetime.now().astimezone(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')}"
    print(expire_at)
    response = requests.post(url, headers=headers, json={
        "username": mac_address,
        "tag": "ROUTER", # service-specific (the tag should exist in the api)
        "expireAt": expire_at,
        "status": "ACTIVE",
        "activeUserInbounds": [
            "e54bcb18-badb-4879-8cbc-71d495c0cbff" # service-specific (the inbound should exist in the api)
        ]
    })
    return response.status_code

def get_vless_link(mac_address):
    url = f"https://{os.getenv('BASE_URL')}/api/subscriptions/by-username/{mac_address}"
    headers = {
        "Authorization": f"Bearer {os.getenv('TOKEN')}"
    }
    response = requests.get(url, headers=headers)
    return response.json()['response']['links'][0] # service-specific (get the first link)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)