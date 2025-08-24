"""
# Trigger rebuild: test for line ending/corruption issue
Twitter Bot for GitHub Actions
--------------------------------
Automates posting tweets, following/unfollowing users, and handles login flows including verification.
Designed for CI/CD environments (GitHub Actions) using Playwright's managed Chromium in headless mode.
All credentials and API keys are loaded from environment variables set as GitHub secrets.
No persistent browser context or local profile is used.
Each workflow run executes a single bot session.
"""

import os
import requests
from random import choice, randint, uniform
from time import sleep
from dotenv import load_dotenv
import logging
from playwright.sync_api import sync_playwright

load_dotenv()

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[logging.StreamHandler()])

USERNAME = os.getenv('MY_USERNAME')
PASSWORD = os.getenv('MY_PASSWORD')
VERIFICATION_EMAIL = os.getenv('VERIFICATION_EMAIL')
PERPLEXITY_API_KEY = os.getenv('PERPLEXITY_API_KEY')
PROMPT = "give me a biased spicy opinion on tech or digital media taken from random famous reddit(recent). only text no numbers at the end , ready to copy paste, under 100 character"

def fetch_text_from_perplexity():
    url = "https://api.perplexity.ai/chat/completions"
    headers = {
        "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "sonar-pro",
        "messages": [
            {"role": "user", "content": PROMPT}
        ]
    }
    try:
        response = requests.post(url, headers=headers, json=data)
        if response.status_code != 200:
            logging.error(f"Perplexity API error {response.status_code}: {response.text}")
            response.raise_for_status()
        result = response.json()
        if 'choices' in result and result['choices'] and 'message' in result['choices'][0]:
            return result['choices'][0]['message']['content']
        else:
            logging.error(f"Unexpected response format: {result}")
            return None
    except Exception as e:
        logging.error(f"Failed to fetch text from Perplexity: {e}")
        return None

def post_text_tweet(page, text):
    try:
        page.goto("https://twitter.com/compose/tweet")
        sleep(uniform(5, 10))
        textarea_selectors = [
            "div[data-testid='tweetTextarea_0']",
            "div[aria-label='Tweet text']",
            "div[role='textbox']",
        ]
        tweet_box_found = False
        for selector in textarea_selectors:
            try:
                print(f"[Bot] Trying textarea selector: {selector}")
                page.wait_for_selector(selector, timeout=30000)
                page.fill(selector, text)
                tweet_box_found = True
                print(f"[Bot] Filled tweet box using selector: {selector}")
                break
            except Exception as e:
                print(f"[Bot] Textarea selector failed: {selector} | Error: {e}")
        if not tweet_box_found:
            print("[Bot] Tweet textarea not found on compose page.")
            logging.error("Tweet textarea not found on compose page.")
            return
        sleep(uniform(2, 4))
        selectors = [
            "div[data-testid='toolBar'] button[data-testid='tweetButtonInline']",
            "button[data-testid='tweetButtonInline']",
            "div[role='button'][data-testid='tweetButtonInline']",
            "button:has-text('Post')",
        ]
        post_clicked = False
        for selector in selectors:
            button = None
            try:
                button = page.wait_for_selector(selector, timeout=20000)
            except Exception as e:
                print(f"[Bot] Post button selector failed: {selector} | Error: {e}")
            if button:
                print("[Bot] Clicking post button...")
                button.click()
                post_clicked = True
                break
        if not post_clicked:
            print("[Bot] Tweet button not found on compose page.")
            logging.error("Tweet button not found on compose page.")
        else:
            print("[Bot] Tweet posted successfully from compose page.")
            logging.info("Tweet posted successfully from compose page.")
        print(f"[Bot] Final page URL after posting: {page.url}")
    except Exception as e:
        print(f"[Bot] Failed to post tweet from compose page: {e}")
        logging.error(f"Failed to post tweet from compose page: {e}")

def follow(page):
    follow_id_list = []  # List of usernames to follow (set as needed)
    try:
        if not follow_id_list:
            logging.info("No follow_id_list provided, skipping follow.")
            return
        random_number = choice(range(len(follow_id_list)))
        page.goto(f"https://twitter.com/{follow_id_list[random_number]}/followers")
        sleep(uniform(5, 10))
        follow_buttons = page.query_selector_all("button[aria-label^='Follow @'][role='button']")
        if not follow_buttons:
            logging.error("No follow buttons found on the page.")
            return
        num_to_follow = randint(1, min(15, len(follow_buttons)))
        followed_count = 0
        for button in range(num_to_follow):
            try:
                follow_buttons[button].click()
                sleep(uniform(2, 5))
                followed_count += 1
            except Exception as e:
                logging.error(f"Error following account number {button + 1}: {e}")
        logging.info(f"Followed {followed_count} accounts.")
    except Exception as e:
        logging.error(f"Error in follow(): {e}")

def unfollow(page):
    try:
        page.goto("https://twitter.com/@/following")
        sleep(uniform(5, 10))
        unfollow_buttons = page.query_selector_all("button[role='button'][aria-label^='Following @']")
        if not unfollow_buttons:
            logging.error("No unfollow buttons found on the page.")
            return
        num_to_unfollow = randint(5, min(10, len(unfollow_buttons)))
        unfollowed_count = 0
        for button in range(num_to_unfollow):
            try:
                unfollow_buttons[button].click()
                sleep(uniform(2, 3))
                page.wait_for_selector("button[role='button'] span:has-text('Unfollow')").click()
                sleep(uniform(2, 5))
                unfollowed_count += 1
            except Exception as e:
                logging.error(f"Error unfollowing account number {button + 1}: {e}")
        logging.info(f"Unfollowed {unfollowed_count} accounts.")
    except Exception as e:
        logging.error(f"Error in unfollow(): {e}")

def main():
    with sync_playwright() as p:
        print("[Bot] Launching browser...")
        browser_type = p.chromium
        browser = browser_type.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        print("[Bot] Navigating to Twitter home page...")
        MAX_LOGIN_ATTEMPTS = 3
        page.goto("https://twitter.com/home")
        print(f"[Bot] Current URL: {page.url}")
        sleep(uniform(5, 10))
        if "/i/flow/login" in page.url or "/?logout" in page.url:
            print("[Bot] Login required. Starting login flow...")
            login_attempts = 0
            while login_attempts < MAX_LOGIN_ATTEMPTS:
                try:
                    print(f"[Bot] Attempt {login_attempts + 1}: Filling username...")
                    page.fill("input[name='text']", USERNAME)
                    sleep(uniform(2, 5))
                    print("[Bot] Clicking Next...")
                    page.click("span:has-text('Next')")
                    sleep(uniform(2, 5))
                    if page.is_visible("input[name='text']") and page.is_visible("span:has-text('Next')"):
                        print("[Bot] Verification required. Filling email...")
                        page.fill("input[name='text']", VERIFICATION_EMAIL)
                        sleep(uniform(2, 4))
                        page.click("span:has-text('Next')")
                        sleep(uniform(2, 4))
                    if page.is_visible("input[name='password']"):
                        print("[Bot] Filling password...")
                        page.fill("input[name='password']", PASSWORD)
                        sleep(uniform(2, 4))
                        print("[Bot] Clicking Log in...")
                        page.click("span:has-text('Log in')")
                        sleep(uniform(5, 10))
                        print("[Bot] Login successful.")
                        break
                except Exception as e:
                    print(f"[Bot] Login attempt {login_attempts + 1} failed: {e}")
                    login_attempts += 1
                    if login_attempts < MAX_LOGIN_ATTEMPTS:
                        print("[Bot] Reloading page for next login attempt...")
                        sleep(uniform(2, 5))
                        page.goto("https://twitter.com/home")
                        print(f"[Bot] Current URL: {page.url}")
                        sleep(uniform(5, 10))
            if login_attempts == MAX_LOGIN_ATTEMPTS:
                print("[Bot] Reached max login attempts. Exiting.")
                return
        print("[Bot] Fetching text from Perplexity...")
        text = fetch_text_from_perplexity()
        if text:
            print(f"[Bot] Text fetched: {text}")
            print("[Bot] Posting tweet...")
            post_text_tweet(page, text)
        else:
            print("[Bot] No text fetched from Perplexity.")
        action = choice(['follow', 'unfollow', 'none'])
        print(f"[Bot] Decided action: {action}")
        if action == 'follow':
            print("[Bot] Following users...")
            follow(page)
        elif action == 'unfollow':
            print("[Bot] Unfollowing users...")
            unfollow(page)
        else:
            print("[Bot] No follow/unfollow action taken this run.")

if __name__ == "__main__":
    main()
