from pywa import WhatsApp, types, filters
from fastapi import FastAPI,Request
import uvicorn
from dotenv import load_dotenv

import os
load_dotenv()

app = FastAPI()
wa = WhatsApp(
    phone_id=os.getenv("PHONE_ID"),
    token=os.getenv("WHATSAPP_TOKEN"),
    server=app,
    callback_url=os.getenv("CALLBACK_URL"),
    verify_token=os.getenv("VERIFY_TOKEN"),
    app_id=int(os.getenv("APP_ID")),
    app_secret=os.getenv("APP_SECRET"),
)

# @wa.on_message(filters.text)
# def new_message(_: WhatsApp, msg: types.Message):
#     msg.reply("Hello from PyWa!")

@app.post("/")
async def raw(request: Request):
    data = await request.json()
    print("RAW WEBHOOK:", data)
    return {"ok": True}
# @wa.on_message()
# def hello_handler(_: WhatsApp, msg: types.Message):
#     msg.react("👋")
#     msg.reply_text(text="Hello from PyWa!", quote=True)
@wa.on_message()
def debug(_: WhatsApp, msg: types.Message):
    print("MESSAGE RECEIVED:", msg)
    msg.reply_text("Received something!")



if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5173)
