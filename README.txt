SMS BOT — RENDER WEBHOOK STARTER

This version is intended for a Render Web Service and uses Telegram webhooks.
It is a starter, not a fully integrated SMS provider product.

DEPLOY:
1. Upload these files to a GitHub repository.
2. On Render, create a new Web Service from that repository.
3. Build command: pip install -r requirements.txt
4. Start command: python bot.py
5. Add environment variables in Render:
   BOT_TOKEN, ADMIN_ID, OTP_GROUP_URL, SUPPORT_URL, WEBHOOK_SECRET
   Render provides PORT and RENDER_EXTERNAL_URL automatically.
6. Deploy, then open your bot and send /start.

IMPORTANT:
- Get Number is not connected until official Lamix API documentation is provided.
- Virtual wallet is a placeholder; no real payment/balance accounting is configured.
- /tmp storage may be lost after redeploy/restart. For persistent data, use a Render persistent disk or managed PostgreSQL and update DB settings.
- Render free instances may sleep or have usage limits; webhook does not guarantee lifetime or uninterrupted free hosting.
- Keep BOT_TOKEN and WEBHOOK_SECRET private.
- Admin commands: /addserver NAME | PRICE, /setrate RATE, /disableserver ID, /stats
