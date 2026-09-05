import hmac, hashlib, json, os
from dotenv import load_dotenv
import requests

load_dotenv()
app_secret = os.environ["WHATSAPP_APP_SECRET"]

body = json.dumps({
  "entry": [{"changes": [{"value": {
    "metadata": {"phone_number_id": "dev-phone-number-id"},
    "messages": [{
      "id": "wamid.TEST0001",
      "from": "923006208750",
      "timestamp": "1735689600",
      "type": "image",
      "image": {
        "id": "fake-media-id-001",
        "caption": "Foundation pour today at Gulberg site"
      }
    }]
  }}]}]
}, separators=(",", ":")).encode()

signature = "sha256=" + hmac.new(
  app_secret.encode(), body, hashlib.sha256
).hexdigest()

resp = requests.post(
  "http://localhost:8015/api/v1/whatsapp/webhook",
  data=body,
  headers={
    "Content-Type": "application/json",
    "X-Hub-Signature-256": signature,
  },
)

print("STATUS:", resp.status_code)
print("BODY:", resp.text)