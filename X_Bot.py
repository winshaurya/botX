def click_dynamic_next_button(page, keywords=["next", "continue", "enter"]):
    """
    Searches for all visible buttons and clicks the first enabled one whose text matches any keyword.
    Returns True if a button was clicked, False otherwise.
    """
    buttons = page.query_selector_all("button[role='button']")
    for btn in buttons:
        try:
            text = btn.inner_text().strip().lower()
            for kw in keywords:
                if kw in text and btn.is_enabled():
                    btn.click()
                    print(f"[Bot] Clicked button with text: {text}")
                    return True
        except Exception as e:
            continue
    print(f"[Bot] No enabled button found for keywords: {keywords}")
    # For debugging: log page HTML if no button found
    logging.debug(page.content())
    return False
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
        # Always navigate to home after login
        page.goto("https://x.com/home")
        sleep(uniform(5, 10))

        # Wait for the tweet box to be visible
        tweet_box_selector = 'div[data-testid="tweetTextarea_0"][contenteditable="true"]'
        try:
            page.wait_for_selector(tweet_box_selector, timeout=40000)
            tweet_box = page.query_selector(tweet_box_selector)
            if tweet_box:
                tweet_box.click()
                sleep(1)
                page.keyboard.type(text)
                print("[Bot] Typed tweet in the box.")
            else:
                raise Exception("Tweet box not found after wait.")
        except Exception as e:
            print(f"[Bot] Failed to find or type in tweet box: {e}")
            logging.error(f"Failed to find or type in tweet box: {e}")
            return

        sleep(uniform(2, 4))

        # Wait for the Post button to be enabled
        post_button_selector = 'button[data-testid="tweetButtonInline"]'
        try:
            page.wait_for_selector(post_button_selector, timeout=20000)
            post_button = page.query_selector(post_button_selector)
            if post_button and post_button.is_enabled():
                post_button.click()
                print("[Bot] Clicked Post button.")
                logging.info("Tweet posted successfully.")
            else:
                raise Exception("Post button not found or not enabled.")
        except Exception as e:
            print(f"[Bot] Failed to click Post button: {e}")
            logging.error(f"Failed to click Post button: {e}")
            return

        print(f"[Bot] Final page URL after posting: {page.url}")

    except Exception as e:
        print(f"[Bot] Failed to post tweet: {e}")
        logging.error(f"Failed to post tweet: {e}")

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
                    page.wait_for_selector("input[name='text']", timeout=20000)
                    page.fill("input[name='text']", USERNAME)
                    sleep(uniform(2, 5))
                    # Dynamically find and click Next/Continue/Enter button
                    page.wait_for_selector("button[role='button']", timeout=20000)
                    click_dynamic_next_button(page)
                    sleep(uniform(2, 5))
                    # Verification email input
                    if page.is_visible("input[data-testid='ocfEnterTextTextInput']"):
                        print("[Bot] Verification required. Filling email...")
                        page.fill("input[data-testid='ocfEnterTextTextInput']", VERIFICATION_EMAIL)
                        sleep(uniform(2, 4))
                        # Dynamically find and click Next/Continue/Enter button after email
                        page.wait_for_selector("button[role='button']", timeout=20000)
                        click_dynamic_next_button(page)
                        sleep(uniform(2, 4))
                    # Password input
                    if page.is_visible("input[name='password']"):
                        print("[Bot] Filling password...")
                        page.fill("input[name='password']", PASSWORD)
                        sleep(uniform(2, 4))
                        # Log in button (data-testid)
                        login_button_selector = "button[data-testid='LoginForm_Login_Button']"
                        page.wait_for_selector(login_button_selector, timeout=20000)
                        login_button = page.query_selector(login_button_selector)
                        if login_button and login_button.is_enabled():
                            print("[Bot] Clicking Log in...")
                            login_button.click()
                        else:
                            print("[Bot] Log in button not enabled, skipping click.")
                        sleep(uniform(5, 10))
                        print("[Bot] Login successful.")
                        break
                except Exception as e:
                    print(f"[Bot] Login attempt {login_attempts + 1} failed: {e}")
                    login_attempts += 1
                    print("[Bot] Reloading page for next login attempt...")
                    sleep(uniform(2, 5))
                    page.goto("https://x.com/i/flow/login")
                    print(f"[Bot] Current URL: {page.url}")
                    sleep(uniform(5, 10))
            if login_attempts == MAX_LOGIN_ATTEMPTS:
                print("[Bot] Reached max login attempts. Exiting.")
                return
        print("[Bot] Fetching text from Perplexity...")
        text = fetch_text_from_perplexity()
        if text:
            print(f"[Bot] Text fetched: {text}")
            print("[Bot] Navigating to home page before posting...")
            page.goto("https://x.com/home", wait_until="networkidle")
            sleep(uniform(5, 10))
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

if __name__ == "__main__":
    main()
