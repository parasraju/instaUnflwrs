# Instagram Unfollow Discord Notifier

A Python tool to notify you via Discord whenever someone unfollows your Instagram account.
It uses a bot Instagram account to monitor your main account’s followers and sends real-time updates to your Discord channel using webhooks.

## 🚀 Features

-Automatic monitoring of Instagram followers
-Discord notifications for every unfollower
-Secure credential management using a .env file
-Easy setup and cross-platform compatibility

## Prerequisites

Python 3.8 or higher
A secondary (bot) Instagram account for login (recommended)
Discord server with webhook access

## 🔧 Installation

1. Clone the repository:
   ```sh
   pip install -r requirements.txt
   ```
2. Edit the .env file 

3. Change:
INSTAGRAM_USERNAME / INSTAGRAM_PASSWORD: Credentials for your bot Instagram account.
TARGET_USERNAME: The Instagram account you want to monitor.
DISCORD_WEBHOOK_URL: Your Discord channel’s webhook URL.
CHECK_INTERVAL: Time between checks in seconds (default: 1800 = 30 minutes).

5. Run the script:
   ```sh
   python unfollow_monitor.py
   ```
Notes & Best Practices
Do not use your main Instagram account for automation to avoid potential bans.
The script stores followers in followers.json (created automatically).
Adjust the CHECK_INTERVAL in your .env file to avoid Instagram rate limits (30+ minutes recommended).
Keep your .env file secure and never commit it to public repositories.

---

Made with ❤️ by Paras Raju

