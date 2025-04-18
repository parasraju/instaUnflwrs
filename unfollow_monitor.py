import os
import time
import json
import requests
import instaloader
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
FOLLOWERS_FILE = "followers.json"
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", 1800))

def get_followers():
    L = instaloader.Instaloader()
    try:
        L.login(
            os.getenv("INSTAGRAM_USERNAME"),
            os.getenv("INSTAGRAM_PASSWORD")
        )
        profile = instaloader.Profile.from_username(
            L.context,
            os.getenv("TARGET_USERNAME")
        )
        return set(follower.username for follower in profile.get_followers())
    except Exception as e:
        print(f"Error fetching followers: {str(e)}")
        return None

def save_followers(followers):
    with open(FOLLOWERS_FILE, "w") as f:
        json.dump(list(followers), f)

def load_previous_followers():
    try:
        with open(FOLLOWERS_FILE, "r") as f:
            return set(json.load(f))
    except FileNotFoundError:
        return set()

def send_discord_notification(unfollowers):
    if not unfollowers:
        return
    webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
    message = f"🚨 **Unfollowers detected:** {', '.join(unfollowers)}"
    requests.post(webhook_url, json={"content": message})

def main():
    while True:
        current_followers = get_followers()
        if current_followers is None:
            time.sleep(60)
            continue

        previous_followers = load_previous_followers()
        unfollowers = previous_followers - current_followers

        if unfollowers:
            send_discord_notification(unfollowers)
            save_followers(current_followers)
        elif not previous_followers:  # First run
            save_followers(current_followers)

        print(f"Checked at {time.ctime()} | Unfollowers: {len(unfollowers)}")
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
