# 🚆 Deploying to Railway

To deploy this bot successfully, follow these steps:

1. **Connect your GitHub Repo** containing this folder (`momentum_bot_railway`).
2. Go to your **Railway Project** -> **Service Settings**.
3. Scroll down to **Root Directory**.
4. Set it to: `/momentum_bot_railway`
5. **Redeploy**.

Railway will now see `requirements.txt` and `Procfile` correctly.

## Or...

If you prefer to deploy via **Railway CLI**:
1. `cd momentum_bot_railway`
2. `railway up`

## Files Included:
- `momentum_bot.py`: The deployment-ready bot.
- `requirements.txt`: Dependencies.
- `Procfile`: Startup command.
- `runtime.txt`: Locked to Python 3.11.0.
