...existing code...
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

# Credentials and API keys from environment variables
USERNAME = os.getenv('MY_USERNAME')
PASSWORD = os.getenv('MY_PASSWORD')
VERIFICATION_EMAIL = os.getenv('VERIFICATION_EMAIL')
PERPLEXITY_API_KEY = os.getenv('PERPLEXITY_API_KEY')
PROMPT = os.getenv('PROMPT')

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

def post_text_tweet(page, text):
    try:
        page.goto("https://twitter.com/compose/tweet")
        sleep(uniform(5, 10))
        page.wait_for_selector("div[data-testid='tweetTextarea_0']", timeout=15000)
        page.fill("div[data-testid='tweetTextarea_0']", text)
        sleep(uniform(2, 4))
        selectors = [
            "div[data-testid='toolBar'] button[data-testid='tweetButtonInline']",
            "button[data-testid='tweetButtonInline']",
            "div[role='button'][data-testid='tweetButtonInline']",
            "button:has-text('Post')",
        ]
        post_clicked = False
        for selector in selectors:
            button = page.query_selector(selector)
            if button:
                button.click()
                post_clicked = True
                break
        if not post_clicked:
            logging.error("Tweet button not found.")
        else:
            logging.info("Tweet posted successfully.")
    except Exception as e:
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
    except Exception as e:
        logging.error(f"Error navigating to the followers page: {e}")
        return
    try:
        follow_buttons = page.query_selector_all("button[aria-label^='Follow @'][role='button']")
        if not follow_buttons:
            logging.error("No follow buttons found on the page.")
            return
        num_to_follow = randint(1, min(15, len(follow_buttons)))
    except Exception as e:
        logging.error(f"Error querying the follow buttons: {e}")
        return
    followed_count = 0
    for button in range(num_to_follow):
        try:
            follow_buttons[button].click()
            sleep(uniform(2, 5))
            followed_count += 1
        except Exception as e:
            logging.error(f"Error following account number {button + 1}: {e}")
    logging.info(f"Followed {followed_count} accounts.")

def unfollow(page):
    try:
        page.goto("https://twitter.com/@/following")
        sleep(uniform(5, 10))
    except Exception as e:
        logging.error(f"Error navigating to the following page: {e}")
        return
    try:
        unfollow_buttons = page.query_selector_all("button[role='button'][aria-label^='Following @']")
        if not unfollow_buttons:
            logging.error("No unfollow buttons found on the page.")
            return
        num_to_unfollow = randint(5, min(10, len(unfollow_buttons)))
    except Exception as e:
        logging.error(f"Error querying the unfollow buttons: {e}")
        return
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

def main():
    with sync_playwright() as p:
        browser_type = p.chromium
        browser = browser_type.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        # Start bot session
        MAX_LOGIN_ATTEMPTS = 3
        page.goto("https://twitter.com/home")
        sleep(uniform(5, 10))
        # Login flow
        if "/i/flow/login" in page.url or "/?logout" in page.url:
            login_attempts = 0
            while login_attempts < MAX_LOGIN_ATTEMPTS:
                try:
                    page.fill("input[name='text']", USERNAME)
                    sleep(uniform(2, 5))
                    page.click("span:has-text('Next')")
                    sleep(uniform(2, 5))
                    # Verification step
                    if page.is_visible("input[name='text']") and page.is_visible("span:has-text('Next')"):
                        page.fill("input[name='text']", VERIFICATION_EMAIL)
                        sleep(uniform(2, 4))
                        page.click("span:has-text('Next')")
                        sleep(uniform(2, 4))
                    # Password step
                    if page.is_visible("input[name='password']"):
                        page.fill("input[name='password']", PASSWORD)
                        sleep(uniform(2, 4))
                        page.click("span:has-text('Log in')")
                        sleep(uniform(5, 10))
                        break
                except Exception as e:
                    logging.error(f"Login attempt {login_attempts + 1} failed due to: {e}")
                    login_attempts += 1
                    if login_attempts < MAX_LOGIN_ATTEMPTS:
                        logging.info("Reloading page for next login attempt...")
                        sleep(uniform(2, 5))
                        page.goto("https://twitter.com/home")
                        sleep(uniform(5, 10))
            if login_attempts == MAX_LOGIN_ATTEMPTS:
                logging.error("Reached max login attempts. Please check your credentials or the page structure.")
                return
        # Post tweet
        text = fetch_text_from_perplexity()
        if text:
            post_text_tweet(page, text)
        else:
            logging.error("No text fetched from Perplexity.")
        # Random follow/unfollow action
        action = choice(['follow', 'unfollow', 'none'])
        if action == 'follow':
            follow(page)
        elif action == 'unfollow':
            unfollow(page)
        else:
            logging.info("No follow/unfollow action taken this run.")

if __name__ == "__main__":
    main()
# Helper function: fetch text from Perplexity API
def fetch_text_from_perplexity():
    url = "https://api.perplexity.ai/chat/completions"
    headers = {
        "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "sonar-pro",
            # Removed stray nested def main()
                    browser_type = p.chromium
                    browser = browser_type.launch(headless=True)
                    context = browser.new_context()
                    page = context.new_page()

                    # Start bot session
                    MAX_LOGIN_ATTEMPTS = 3
                    page.goto("https://twitter.com/home")
                    sleep(uniform(5, 10))
                    # Login flow
                    if "/i/flow/login" in page.url or "/?logout" in page.url:
                        login_attempts = 0
                        while login_attempts < MAX_LOGIN_ATTEMPTS:
                            try:
                                page.fill("input[name='text']", USERNAME)
                                sleep(uniform(2, 5))
                                page.click("span:has-text('Next')")
                                sleep(uniform(2, 5))
                                # Verification step
                                if page.is_visible("input[name='text']") and page.is_visible("span:has-text('Next')"):
                                    page.fill("input[name='text']", VERIFICATION_EMAIL)
                                    sleep(uniform(2, 4))
                                    page.click("span:has-text('Next')")
                                    sleep(uniform(2, 4))
                                # Password step
                                if page.is_visible("input[name='password']"):
                                    page.fill("input[name='password']", PASSWORD)
                                    sleep(uniform(2, 4))
                                    page.click("span:has-text('Log in')")
                                    sleep(uniform(5, 10))
                                    break
                            except Exception as e:
                                logging.error(f"Login attempt {login_attempts + 1} failed due to: {e}")
                                login_attempts += 1
                                if login_attempts < MAX_LOGIN_ATTEMPTS:
                                    logging.info("Reloading page for next login attempt...")
                                    sleep(uniform(2, 5))
                                    page.goto("https://twitter.com/home")
                                    sleep(uniform(5, 10))
                        if login_attempts == MAX_LOGIN_ATTEMPTS:
                            logging.error("Reached max login attempts. Please check your credentials or the page structure.")
                            return
                    # Post tweet
                    text = fetch_text_from_perplexity()
                    if text:
                        post_text_tweet(page, text)
                    else:
                        logging.error("No text fetched from Perplexity.")
                    # Random follow/unfollow action
                    action = choice(['follow', 'unfollow', 'none'])
                    if action == 'follow':
                        follow(page)
                    elif action == 'unfollow':
                        unfollow(page)
                    else:
                        logging.info("No follow/unfollow action taken this run.")

            Twitter Bot for GitHub Actions
            --------------------------------
            Automates posting tweets, following/unfollowing users, and handles login flows including verification.
            Designed for CI/CD environments (GitHub Actions) using Playwright's managed Chromium in headless mode.
            All credentials and API keys are loaded from environment variables set as GitHub secrets.
            No persistent browser context or local profile is used.
            Each workflow run executes a single bot session.
            """

            import os  # For environment variables
            import requests  # For API requests
            from random import choice, randint, uniform  # For randomization
            from time import sleep  # For delays
            from dotenv import load_dotenv  # For loading .env variables
            import logging  # For logging info/errors
            from playwright.sync_api import sync_playwright  # For browser automation
            response.raise_for_status()
        # Twitter Bot for GitHub Actions
        return result['choices'][0]['message']['content']
    except Exception as e:
        logging.error(f"Failed to fetch text from Perplexity: {e}")
        return None

# Helper function: post a text tweet
def post_text_tweet(text):
    try:
        page.goto("https://twitter.com/compose/tweet")
        sleep(uniform(5, 10))
        page.wait_for_selector("div[data-testid='tweetTextarea_0']", timeout=15000)
        page.fill("div[data-testid='tweetTextarea_0']", text)
        sleep(uniform(2, 4))
        selectors = [
            "div[data-testid='toolBar'] button[data-testid='tweetButtonInline']",
            "button[data-testid='tweetButtonInline']",
            "div[role='button'][data-testid='tweetButtonInline']",
            "button:has-text('Post')",
        ]
        post_clicked = False
        for selector in selectors:
            try:
                button = page.query_selector(selector)
                if button:
                    button.scroll_into_view_if_needed()
                    sleep(1)
                    if button.is_enabled():
                        button.click()
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

                    # Credentials and API keys from environment variables
                    USERNAME = os.getenv('MY_USERNAME')
                    PASSWORD = os.getenv('MY_PASSWORD')
                    VERIFICATION_EMAIL = os.getenv('VERIFICATION_EMAIL')
                    PERPLEXITY_API_KEY = os.getenv('PERPLEXITY_API_KEY')
                    PROMPT = os.getenv('PROMPT')

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

                    def post_text_tweet(page, text):
                        try:
                            page.goto("https://twitter.com/compose/tweet")
                            sleep(uniform(5, 10))
                            page.wait_for_selector("div[data-testid='tweetTextarea_0']", timeout=15000)
                            page.fill("div[data-testid='tweetTextarea_0']", text)
                            sleep(uniform(2, 4))
                            selectors = [
                                "div[data-testid='toolBar'] button[data-testid='tweetButtonInline']",
                                "button[data-testid='tweetButtonInline']",
                                "div[role='button'][data-testid='tweetButtonInline']",
                                "button:has-text('Post')",
                            ]
                            post_clicked = False
                            for selector in selectors:
                                button = page.query_selector(selector)
                                if button:
                                    button.click()
                                    post_clicked = True
                                    break
                            if not post_clicked:
                                logging.error("Tweet button not found.")
                            else:
                                logging.info("Tweet posted successfully.")
                        except Exception as e:
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
                        except Exception as e:
                            logging.error(f"Error navigating to the followers page: {e}")
                            return
                        try:
                            follow_buttons = page.query_selector_all("button[aria-label^='Follow @'][role='button']")
                            if not follow_buttons:
                                logging.error("No follow buttons found on the page.")
                                return
                            num_to_follow = randint(1, min(15, len(follow_buttons)))
                        except Exception as e:
                            logging.error(f"Error querying the follow buttons: {e}")
                            return
                        followed_count = 0
                        for button in range(num_to_follow):
                            try:
                                follow_buttons[button].click()
                                sleep(uniform(2, 5))
                                followed_count += 1
                            except Exception as e:
                                logging.error(f"Error following account number {button + 1}: {e}")
                        logging.info(f"Followed {followed_count} accounts.")

                    def unfollow(page):
                        try:
                            page.goto("https://twitter.com/@/following")
                            sleep(uniform(5, 10))
                        except Exception as e:
                            logging.error(f"Error navigating to the following page: {e}")
                            return
                        try:
                            unfollow_buttons = page.query_selector_all("button[role='button'][aria-label^='Following @']")
                            if not unfollow_buttons:
                                logging.error("No unfollow buttons found on the page.")
                                return
                            num_to_unfollow = randint(5, min(10, len(unfollow_buttons)))
                        except Exception as e:
                            logging.error(f"Error querying the unfollow buttons: {e}")
                            return
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

                    def main():
                        with sync_playwright() as p:
                            browser_type = p.chromium
                            browser = browser_type.launch(headless=True)
                            context = browser.new_context()
                            page = context.new_page()

                            # Start bot session
                            MAX_LOGIN_ATTEMPTS = 3
                            page.goto("https://twitter.com/home")
                            sleep(uniform(5, 10))
                            # Login flow
                            if "/i/flow/login" in page.url or "/?logout" in page.url:
                                login_attempts = 0
                                while login_attempts < MAX_LOGIN_ATTEMPTS:
                                    try:
                                        page.fill("input[name='text']", USERNAME)
                                        sleep(uniform(2, 5))
                                        page.click("span:has-text('Next')")
                                        sleep(uniform(2, 5))
                                        # Verification step
                                        if page.is_visible("input[name='text']") and page.is_visible("span:has-text('Next')"):
                                            page.fill("input[name='text']", VERIFICATION_EMAIL)
                                            sleep(uniform(2, 4))
                                            page.click("span:has-text('Next')")
                                            sleep(uniform(2, 4))
                                        # Password step
                                        if page.is_visible("input[name='password']"):
                                            page.fill("input[name='password']", PASSWORD)
                                            sleep(uniform(2, 4))
                                            page.click("span:has-text('Log in')")
                                            sleep(uniform(5, 10))
                                            break
                                    except Exception as e:
                                        logging.error(f"Login attempt {login_attempts + 1} failed due to: {e}")
                                        login_attempts += 1
                                        if login_attempts < MAX_LOGIN_ATTEMPTS:
                                            logging.info("Reloading page for next login attempt...")
                                            sleep(uniform(2, 5))
                                            page.goto("https://twitter.com/home")
                                            sleep(uniform(5, 10))
                                if login_attempts == MAX_LOGIN_ATTEMPTS:
                                    logging.error("Reached max login attempts. Please check your credentials or the page structure.")
                                    return
                            # Post tweet
                            text = fetch_text_from_perplexity()
                            if text:
                                post_text_tweet(page, text)
                            else:
                                logging.error("No text fetched from Perplexity.")
                            # Random follow/unfollow action
                            action = choice(['follow', 'unfollow', 'none'])
                            if action == 'follow':
                                follow(page)
                            elif action == 'unfollow':
                                unfollow(page)
                            else:
                                logging.info("No follow/unfollow action taken this run.")

                    if __name__ == "__main__":
                        main()
            logging.error("No text fetched from Perplexity.")
        # Random follow/unfollow action
        action = choice(['follow', 'unfollow', 'none'])
        if action == 'follow':
            follow()
        elif action == 'unfollow':
            unfollow()
        else:
            logging.info("No follow/unfollow action taken this run.")
        
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

    def follow():
        follow_id_list = []  # List of usernames to follow (set as needed)
        try:
            if not follow_id_list:
                logging.info("No follow_id_list provided, skipping follow.")
                return
            random_number = choice(range(len(follow_id_list)))
            page.goto(f"https://twitter.com/{follow_id_list[random_number]}/followers")
            sleep(uniform(5, 10))
        except Exception as e:
            logging.error(f"Error navigating to the followers page: {e}")
            return
        try:
            follow_buttons = page.query_selector_all("button[aria-label^='Follow @'][role='button']")
            if not follow_buttons:
                logging.error("No follow buttons found on the page.")
                return
            num_to_follow = randint(1, min(15, len(follow_buttons)))
        except Exception as e:
            logging.error(f"Error querying the follow buttons: {e}")
            return

        followed_count = 0  # To keep track of the number of successful follows

        # Follow random number of accounts
        for button in range(num_to_follow):
            try:
                follow_buttons[button].click()
                sleep(uniform(2, 5))
                followed_count += 1
            except Exception as e:
                logging.error(f"Error following account number {button + 1}: {e}")

        logging.info(f"Followed {followed_count} accounts.")

    def unfollow():
        try:
            page.goto("https://twitter.com/@/following")
            sleep(uniform(5, 10))
        except Exception as e:
            logging.error(f"Error navigating to the following page: {e}")
            return
        try:
            unfollow_buttons = page.query_selector_all("button[role='button'][aria-label^='Following @']")
            if not unfollow_buttons:
                logging.error("No unfollow buttons found on the page.")
                return
            num_to_unfollow = randint(5, min(10, len(unfollow_buttons)))
        except Exception as e:
            logging.error(f"Error querying the unfollow buttons: {e}")
            return

        unfollowed_count = 0  # To keep track of the number of successful unfollows

        # Unfollow a random number of accounts
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


def main():
    with sync_playwright() as p:
        browser_type = p.chromium
        browser = browser_type.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        # Start bot session
        MAX_LOGIN_ATTEMPTS = 3
        page.goto("https://twitter.com/home")
        sleep(uniform(5, 10))
        # Login flow
        if "/i/flow/login" in page.url or "/?logout" in page.url:
            login_attempts = 0
            while login_attempts < MAX_LOGIN_ATTEMPTS:
                try:
                    page.fill("input[name='text']", USERNAME)
                    sleep(uniform(2, 5))
                    page.click("span:has-text('Next')")
                    sleep(uniform(2, 5))
                    # Verification step
                    if page.is_visible("input[name='text']") and page.is_visible("span:has-text('Next')"):
                        page.fill("input[name='text']", VERIFICATION_EMAIL)
                        sleep(uniform(2, 4))
                        page.click("span:has-text('Next')")
                        sleep(uniform(2, 4))
                    # Password step
                    if page.is_visible("input[name='password']"):
                        page.fill("input[name='password']", PASSWORD)
                        sleep(uniform(2, 4))
                        page.click("span:has-text('Log in')")
                        sleep(uniform(5, 10))
                        break
                except Exception as e:
                    logging.error(f"Login attempt {login_attempts + 1} failed due to: {e}")
                    login_attempts += 1
                    if login_attempts < MAX_LOGIN_ATTEMPTS:
                        logging.info("Reloading page for next login attempt...")
                        sleep(uniform(2, 5))
                        page.goto("https://twitter.com/home")
                        sleep(uniform(5, 10))
            if login_attempts == MAX_LOGIN_ATTEMPTS:
                logging.error("Reached max login attempts. Please check your credentials or the page structure.")
                return
        # Post tweet
        text = fetch_text_from_perplexity()
        if text:
            post_text_tweet(page, text)
        else:
            logging.error("No text fetched from Perplexity.")
        # Random follow/unfollow action
        action = choice(['follow', 'unfollow', 'none'])
        if action == 'follow':
            follow(page)
        elif action == 'unfollow':
            unfollow(page)
        else:
            logging.info("No follow/unfollow action taken this run.")

if __name__ == "__main__":
    main()
