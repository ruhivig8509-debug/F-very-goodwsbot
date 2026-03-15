# 🌸 Ruhi Ji — Savage Queen Telegram Bot

A dual-personality AI chatbot powered by Kimi-K2-Instruct via Hugging Face Router API,
with persistent PostgreSQL memory, deployed on Render.com.

## Setup Instructions

### 1. Prerequisites
- Python 3.10+
- PostgreSQL database (Neon.tech recommended)
- Telegram Bot Token (from @BotFather)
- Hugging Face API Token

### 2. Environment Variables

Create a `.env` file (for local development) or set these in Render's dashboard:

```env
TELEGRAM_BOT_TOKEN=your_bot_token
HF_TOKEN=your_huggingface_token
DATABASE_URL=postgresql://user:pass@host/dbname?sslmode=require
OWNER_USERNAME=RUHI_VIG_QNR
PORT=10000
```

> ⚠️ **SECURITY**: Never commit `.env` or credentials to version control.
> Add `.env` to your `.gitignore`.

### 3. Local Development

```bash
pip install -r requirements.txt
python bot.py
```

### 4. Deploy to Render

1. Push code to a GitHub repository
2. Create a **Web Service** on Render
3. Set **Build Command**: `pip install -r requirements.txt`
4. Set **Start Command**: `python bot.py`
5. Add all environment variables in Render's Environment tab
6. Deploy!

### 5. Keep-Alive (UptimeRobot)

Since Render's free tier spins down after 15 minutes of inactivity:
1. Sign up at [UptimeRobot](https://uptimerobot.com)
2. Add a new HTTP monitor pointing to your Render URL's `/health` endpoint
3. Set check interval to 5 minutes

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐
│  Telegram    │────▶│   bot.py     │────▶│  Hugging Face   │
│  Users       │◀────│  (handlers)  │◀────│  Router API     │
└─────────────┘     └──────┬───────┘     └─────────────────┘
                           │
                    ┌──────▼───────┐
                    │  PostgreSQL  │
                    │  (Neon.tech) │
                    └──────────────┘
```

## Features
- 🧠 Dual personality (Sweet for Owner, Savage for others)
- 💾 Persistent memory (20 msgs group / 50 msgs private)
- 🗣️ Wake phrase activation ("Ruhi Ji")
- 👑 Full admin dashboard
- 🚫 Bad word filtering
- 📢 Broadcast system
- 🏥 Health check endpoint for Render

## License
MIT
