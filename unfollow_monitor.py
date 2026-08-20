import os
import sys
import time
import json
import signal
import logging
import argparse
import requests
import instaloader
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

FOLLOWERS_FILE = "followers.json"
MAX_DISCORD_MSG_LENGTH = 1900

def setup_logging(verbose):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

def validate_required_env():
    required = [
        "INSTAGRAM_USERNAME",
        "INSTAGRAM_PASSWORD",
        "DISCORD_WEBHOOK_URL"
    ]
    missing = [v for v in required if not os.getenv(v)]
    if missing:
        logging.error("Missing required env vars: %s", ", ".join(missing))
        sys.exit(1)

def parse_check_interval(raw):
    try:
        interval = int(raw)
    except (TypeError, ValueError):
        logging.error("CHECK_INTERVAL must be an integer, got: %s", raw)
        sys.exit(1)
    if interval <= 0:
        logging.error("CHECK_INTERVAL must be a positive integer, got: %s", raw)
        sys.exit(1)
    return interval

def login(L):
    L.login(os.getenv("INSTAGRAM_USERNAME"), os.getenv("INSTAGRAM_PASSWORD"))

def get_followers(L):
    profile = instaloader.Profile.from_username(
        L.context, L.context.username
    )
    return set(follower.username for follower in profile.get_followers())

def save_followers(followers):
    with open(FOLLOWERS_FILE, "w") as f:
        json.dump(list(followers), f)
    logging.info("Saved %d followers to %s", len(followers), FOLLOWERS_FILE)

def load_previous_followers():
    try:
        with open(FOLLOWERS_FILE, "r") as f:
            data = json.load(f)
    except FileNotFoundError:
        return None
    except json.JSONDecodeError as e:
        logging.error("Corrupt followers file %s: %s", FOLLOWERS_FILE, e)
        sys.exit(1)
    if not isinstance(data, list):
        logging.error("Corrupt followers file %s: expected a JSON list", FOLLOWERS_FILE)
        sys.exit(1)
    return set(data)

def truncate(text, limit=MAX_DISCORD_MSG_LENGTH):
    if len(text) > limit:
        return text[:limit] + "..."
    return text

def send_discord_notification(unfollowers, new_followers):
    webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
    embeds = []

    if unfollowers:
        embeds.append({
            "title": "Unfollowers Detected",
            "description": truncate(", ".join(unfollowers)),
            "color": 0xFF4444,
            "footer": {"text": f"Total: {len(unfollowers)}"},
            "timestamp": datetime.utcnow().isoformat() + "Z"
        })

    if new_followers:
        embeds.append({
            "title": "New Followers",
            "description": truncate(", ".join(new_followers)),
            "color": 0x44FF44,
            "footer": {"text": f"Total: {len(new_followers)}"},
            "timestamp": datetime.utcnow().isoformat() + "Z"
        })

    if not embeds:
        return True

    try:
        resp = requests.post(webhook_url, json={"embeds": embeds}, timeout=10)
        resp.raise_for_status()
        logging.info(
            "Discord notification sent: %d unfollowers, %d new followers",
            len(unfollowers), len(new_followers)
        )
        return True
    except requests.RequestException as e:
        logging.error("Failed to send Discord notification: %s", e)
        return False

def main():
    parser = argparse.ArgumentParser(
        description="Instagram Unfollow Discord Notifier"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Enable debug logging"
    )
    parser.add_argument(
        "--once", "-o", action="store_true",
        help="Run once and exit"
    )
    parser.add_argument(
        "--interval", "-i", type=int, default=None,
        help="Check interval in seconds (overrides .env)"
    )
    args = parser.parse_args()

    setup_logging(args.verbose)
    validate_required_env()
    if args.interval is not None:
        check_interval = parse_check_interval(args.interval)
    else:
        check_interval = parse_check_interval(os.getenv("CHECK_INTERVAL", "1800"))

    logging.info("Starting Instagram Unfollow Discord Notifier")

    L = instaloader.Instaloader()
    username = os.getenv("INSTAGRAM_USERNAME")
    session_file = f"session-{username}"

    try:
        L.load_session_from_file(username, session_file)
        logging.info("Loaded saved session from %s", session_file)
    except FileNotFoundError:
        logging.info("No saved session found, logging in...")
        login(L)
        L.save_session_to_file(session_file)
        logging.info("Session saved to %s", session_file)

    shutdown = False
    current_followers = None
    persist_on_exit = True

    def handle_shutdown(sig, frame):
        nonlocal shutdown
        logging.info("Shutdown signal received, saving state...")
        shutdown = True

    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)

    while not shutdown:
        try:
            current_followers = get_followers(L)
            logging.info("Fetched %d followers", len(current_followers))
        except Exception as e:
            logging.error("Error fetching followers: %s", e)
            if args.once:
                break
            time.sleep(60)
            continue

        previous_followers = load_previous_followers()

        if previous_followers is None:
            unfollowers = set()
            new_followers = set()
            save_followers(current_followers)
            persist_on_exit = True
            logging.info("First run — saved initial follower snapshot")
        else:
            unfollowers = previous_followers - current_followers
            new_followers = current_followers - previous_followers
            if unfollowers or new_followers:
                if send_discord_notification(unfollowers, new_followers):
                    save_followers(current_followers)
                    persist_on_exit = True
                else:
                    persist_on_exit = False
                    logging.warning(
                        "Keeping previous snapshot until Discord notification succeeds"
                    )

        logging.info(
            "Checked at %s | Unfollowers: %d | New: %d",
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            len(unfollowers), len(new_followers)
        )

        if args.once:
            break

        for _ in range(check_interval // 5):
            if shutdown:
                break
            time.sleep(5)
        if not shutdown and check_interval % 5:
            time.sleep(check_interval % 5)

    if current_followers is not None and persist_on_exit:
        save_followers(current_followers)
    logging.info("Shutdown complete")

if __name__ == "__main__":
    main()
