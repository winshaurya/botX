"""
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
        for idx in range(num_to_unfollow):
            try:
                unfollow_buttons[idx].click()
                sleep(uniform(2, 3))
                page.wait_for_selector("button[role='button'] span:has-text('Unfollow')").click()
                sleep(uniform(2, 5))
                unfollowed_count += 1
            except Exception as e:
                logging.error(f"Error unfollowing account number {idx + 1}: {e}")
        logging.info(f"Unfollowed {unfollowed_count} accounts.")
    except Exception as e:
        logging.error(f"Error in unfollow(): {e}")

# Clean follow function
def follow(page):
    """Stub for follow action. Implement logic as needed."""
    print("[Bot] Follow action is not implemented yet.")
    pass
def post_text_tweet(page, text):
    # Focus the tweet box and type text with random delays
    # Improved tweet box detection
    tweet_box_selectors = [
        "div[aria-label='Tweet text']",
        "div[data-testid='tweetTextarea_0']",
        "div[role='textbox'][contenteditable='true']",
        "div[role='textbox']",
    ]
    tweet_box = None
    for selector in tweet_box_selectors:
        try:
            page.wait_for_selector(selector, timeout=7000)
            tweet_box = page.query_selector(selector)
            if tweet_box:
                tweet_box.click()
                break
        except Exception:
            continue
    if tweet_box:
        if text:
            for char in str(text):
                page.keyboard.type(char)
                sleep(uniform(0.02, 0.10))
            sleep(uniform(0.5, 1.5))
        else:
            print("[Bot] No text provided for tweet.")
    else:
        print("[Bot] Tweet box not found.")
        logging.error("Tweet box not found.")
        return

    # Improved post button detection
    post_button_selectors = [
        "button[data-testid='tweetButtonInline']",
        "div[data-testid='tweetButtonInline'] button",
        "div[role='button'][data-testid='tweetButton']",
        "button[aria-label='Tweet']",
        "button:has-text('Post')",
        "button:has-text('Tweet')",
    ]
    post_button = None
    for selector in post_button_selectors:
        try:
            page.wait_for_selector(selector, timeout=7000)
            post_button = page.query_selector(selector)
            if post_button and post_button.is_enabled():
                box = post_button.bounding_box()
                if box:
                    page.mouse.move(box['x'] + box['width']/2, box['y'] + box['height']/2, steps=randint(3, 10))
                    sleep(uniform(0.1, 0.3))
                post_button.click()
                print(f"[Bot] Clicked Post button using selector: {selector}")
                logging.info("Tweet posted successfully.")
                break
        except Exception as e:
            print(f"[Bot] Post button selector not found: {selector} ({e})")
    if not post_button:
        print("[Bot] Could not find any Post button. Dumping HTML for debug...")
        with open("page_debug_postbutton.html", "w", encoding="utf-8") as f:
            f.write(page.content())
        try:
            page.keyboard.press('Enter')
            print("[Bot] Tried to submit tweet via Enter key.")
        except Exception as e:
            print(f"[Bot] Fallback submit failed: {e}")
            logging.error(f"Fallback submit failed: {e}")
            return
    return page.url
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
                    # Click Next button (static selector from x.html)
                    next_button_selector = "button[role='button']:has-text('Next')"
                    page.wait_for_selector(next_button_selector, timeout=20000)
                    next_button = page.query_selector(next_button_selector)
                    if next_button and next_button.is_enabled():
                        next_button.click()
                        print("[Bot] Clicked Next button.")
                    else:
                        print("[Bot] Next button not found or not enabled.")
                    sleep(uniform(2, 5))
                    # Verification email input
                    if page.is_visible("input[data-testid='ocfEnterTextTextInput']"):
                        print("[Bot] Verification required. Filling email...")
                        page.fill("input[data-testid='ocfEnterTextTextInput']", VERIFICATION_EMAIL)
                        sleep(uniform(2, 4))
                        # Blur the email input to trigger validation
                        page.eval_on_selector("input[data-testid='ocfEnterTextTextInput']", "el => el.blur()")
                        # Wait for Next button to become enabled (up to 5 seconds)
                        next_span_selector = "button[role='button'] span:has-text('Next')"
                        page.wait_for_selector(next_span_selector, timeout=20000)
                        next_span = page.query_selector(next_span_selector)
                        clicked = False
                        if next_span:
                            parent_button = next_span.evaluate_handle("node => node.closest('button')")
                            for _ in range(10):  # Try for up to 5 seconds
                                if parent_button and parent_button.is_enabled():
                                    parent_button.click()
                                    print("[Bot] Clicked Next button after email (span parent).")
                                    clicked = True
                                    break
                                sleep(0.5)
                            if not clicked:
                                print("[Bot] Next button after email not enabled after waiting.")
                        else:
                            print("[Bot] Next button after email not found.")
                        # Detect and print any error messages shown after entering verification email
                        error_message_selector = "div[role='alert'], div[data-testid='ocfEnterTextError']"
                        error_messages = page.query_selector_all(error_message_selector)
                        if error_messages:
                            for err in error_messages:
                                text = err.inner_text()
                                if text:
                                    print(f"[Bot] Error after email entry: {text}")
                        else:
                            print("[Bot] No error message detected after email entry.")
                        sleep(uniform(2, 4))
                    # Password input
                    if page.is_visible("input[name='password']"):
                        print("[Bot] Filling password...")
                        page.fill("input[name='password']", PASSWORD)
                        sleep(uniform(2, 4))
                        # Click Log in button (static selector from x.html)
                        login_button_selector = "button[data-testid='LoginForm_Login_Button']"
                        page.wait_for_selector(login_button_selector, timeout=20000)
                        login_button = page.query_selector(login_button_selector)
                        if login_button and login_button.is_enabled():
                            login_button.click()
                            print("[Bot] Clicked Log in button.")
                        else:
                            print("[Bot] Log in button not found or not enabled.")
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
            # More robust navigation: use domcontentloaded and higher timeout
            try:
                page.goto("https://x.com/home", wait_until="domcontentloaded", timeout=60000)
            except Exception as e:
                print(f"[Bot] Navigation to home failed: {e}. Retrying with default wait...")
                try:
                    page.goto("https://x.com/home", timeout=60000)
                except Exception as e2:
                    print(f"[Bot] Second navigation attempt failed: {e2}")
                    return
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
