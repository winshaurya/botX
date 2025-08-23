from playwright.sync_api import sync_playwright
import os
from time import sleep, time
import requests
from random import choice, randint, uniform
from dotenv import load_dotenv
import re
import logging
import json


load_dotenv()

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[logging.StreamHandler()])


# Use environment variables set by GitHub Actions secrets. Default to Linux paths if not set.
USERNAME = os.getenv('MY_USERNAME')
PASSWORD = os.getenv('MY_PASSWORD')
# Use Linux-compatible default for CI
PROFILE_PATH = os.getenv('PROFILE_PATH', '/home/runner/work/botX/profile')
PERPLEXITY_API_KEY = os.getenv('PERPLEXITY_API_KEY')
PERPLEXITY_API_URL = "https://api.perplexity.ai/chat/completions"  # Updated endpoint per docs


def get_perplexity_answer(prompt):
    if not PERPLEXITY_API_KEY:
        logging.error("Perplexity API key not set in environment variables.")
        return None
    headers = {
        "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "sonar-pro",  # Use a valid model name per docs
        "messages": [{"role": "user", "content": prompt}]
    }
    try:
        response = requests.post(PERPLEXITY_API_URL, headers=headers, data=json.dumps(data))
        if response.status_code == 200:
            result = response.json()
            return result['choices'][0]['message']['content']
        else:
            logging.error(f"Perplexity API error: {response.text}")
            return None
    except Exception as e:
        logging.error(f"Error calling Perplexity API: {e}")
        return None


def main():
    with sync_playwright() as p:
        browser_type = p.chromium
        context = browser_type.launch_persistent_context(
            user_data_dir=PROFILE_PATH,
            headless=True,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-infobars',
                '--ignore-certificate-errors',
                '--use-gl=egl',
                '--ignore-gpu-blocklist',
                '--use-gl=angle',
            ]
        )
        page = context.new_page()

        def post_tweet(file_path):
            try:
                page.goto("https://x.com/home")
                page.wait_for_timeout(randint(8000, 15000))
            except Exception as e:
                logging.error(f"An error occurred while navigating to the post page: {e}")
                return
            try:
                if not os.path.exists(file_path):
                    logging.error(f"The file {file_path} does not exist.")
                    return
                page.set_input_files("input[data-testid='fileInput']", file_path)
                page.wait_for_timeout(randint(15000, 25000))
                post_button = page.wait_for_selector("button[data-testid='tweetButtonInline']", timeout=15000)
                for _ in range(10):
                    if post_button.is_enabled():
                        post_button.click()
                        page.wait_for_timeout(randint(4000, 8000))
                        break
                    page.wait_for_timeout(1500)
                else:
                    logging.error("Post button found but never enabled.")
            except Exception as e:
                logging.error(f"An error occurred while posting the tweet: {e}")

        def post_text_tweet(text):
            try:
                page.goto("https://x.com/home")
                page.wait_for_timeout(randint(8000, 15000))
                # Check login status before posting
                if "/i/flow/login" in page.url or "/?logout" in page.url:
                    logging.error(f"Not logged in! Current URL: {page.url}")
                    # Optionally, try to login here or skip
                    return
                try:
                    tweet_box = page.wait_for_selector("div[data-testid='tweetTextarea_0']", timeout=10000)
                except Exception as e:
                    logging.error(f"Tweet box not found. URL: {page.url}")
                    # Save page HTML for debugging
                    with open("debug_tweetbox.html", "w", encoding="utf-8") as f:
                        f.write(page.content())
                    return
                tweet_box.click()
                page.keyboard.type(text)
                page.wait_for_timeout(randint(3000, 6000))
                post_button = page.wait_for_selector("button[data-testid='tweetButtonInline']", timeout=15000)
                for _ in range(10):
                    if post_button.is_enabled():
                        post_button.click()
                        page.wait_for_timeout(randint(4000, 8000))
                        break
                    page.wait_for_timeout(1500)
                else:
                    logging.error("Post button found but never enabled.")
            except Exception as e:
                logging.error(f"Error posting text tweet: {e}")

        # ...existing code for fetchPost, follow, unfollow can be similarly refactored...

        script_start_time = time()
        MAX_LOGIN_ATTEMPTS = 3

        while True:
            page.goto("https://twitter.com/home")
            page.wait_for_timeout(randint(8000, 15000))

            if "/i/flow/login" in page.url or "/?logout" in page.url:
                login_attempts = 0
                while login_attempts < MAX_LOGIN_ATTEMPTS:
                    try:
                        page.fill("input[name='text']", USERNAME)
                        page.wait_for_timeout(randint(3000, 7000))
                        page.click("span:has-text('Next')")
                        page.wait_for_timeout(randint(3000, 7000))
                        page.wait_for_selector("input[name='password']").fill(PASSWORD)
                        page.wait_for_timeout(randint(3000, 7000))
                        page.click("span:has-text('Log in')")
                        page.wait_for_timeout(randint(7000, 15000))
                        break
                    except Exception as e:
                        logging.error(f"Login attempt {login_attempts + 1} failed due to: {e}")
                        login_attempts += 1
                        if login_attempts < MAX_LOGIN_ATTEMPTS:
                            logging.info("Reloading page for next login attempt...")
                            page.wait_for_timeout(randint(3000, 7000))
                            page.goto("https://twitter.com/home")
                            page.wait_for_timeout(randint(8000, 15000))
                if login_attempts == MAX_LOGIN_ATTEMPTS:
                    logging.error("Reached max login attempts. Please check your credentials or the page structure.")
                    break

            num_of_posts_today = randint(4, 6)
            avg_interval = 86400 / num_of_posts_today
            start_time = time()

            while num_of_posts_today > 0 and (time() - start_time) < 86400:
                prompt = "Write a motivational quote for Twitter."
                answer = get_perplexity_answer(prompt)
                if answer:
                    post_text_tweet(answer)
                    logging.info(f"Tweeted Perplexity answer: {answer}")
                sleep_time = randint(int(0.8 * avg_interval), int(1.2 * avg_interval))
                page.wait_for_timeout(sleep_time * 1000)
                num_of_posts_today -= 1

            while (time() - start_time) < 86400:
                page.wait_for_timeout(600000)

if __name__ == "__main__":
    main()