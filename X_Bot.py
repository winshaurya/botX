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
# Use phone/email for verification if required
USERNAME = os.getenv('MY_USERNAME')
PASSWORD = os.getenv('MY_PASSWORD')
VERIFICATION_ID = os.getenv('MY_VERIFICATION_ID', USERNAME)  # fallback to username
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
    # Helper: Try to detect and respond to Twitter's prompt/question
    def handle_twitter_prompt():
        prompt_text = None
        try:
            # Try to find the main prompt/question
            prompt_elem = page.query_selector("div[role='alert'], div[role='dialog'] span, div[role='dialog'] div")
            if prompt_elem:
                prompt_text = prompt_elem.inner_text().strip()
                logging.info(f"Twitter prompt: {prompt_text}")
        except Exception:
            pass
        # Respond to known prompts
        if prompt_text:
            if "phone number" in prompt_text or "email address" in prompt_text or "verify" in prompt_text:
                logging.info("Detected prompt for phone/email. Filling VERIFICATION_ID...")
                input_elem = None
                try:
                    input_elem = page.wait_for_selector("input[name='text']", timeout=5000)
                except Exception:
                    pass
                if input_elem and input_elem.is_visible():
                    input_elem.fill(VERIFICATION_ID)
                    page.wait_for_timeout(randint(3000, 7000))
                    page.click("span:has-text('Next')")
                    page.wait_for_timeout(randint(3000, 7000))
                    return True
            if "password" in prompt_text:
                logging.info("Detected prompt for password. Filling PASSWORD...")
                password_elem = None
                selectors = [
                    "input[name='password']",
                    "input[type='password']",
                    "input[autocomplete='current-password']"
                ]
                for sel in selectors:
                    try:
                        password_elem = page.wait_for_selector(sel, timeout=5000)
                        if password_elem:
                            break
                    except Exception:
                        continue
                if password_elem and password_elem.is_visible():
                    password_elem.fill(PASSWORD)
                    page.wait_for_timeout(randint(3000, 7000))
                    page.click("span:has-text('Log in')")
                    page.wait_for_timeout(randint(7000, 15000))
                    return True
        return False

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
                # Add logic to submit the tweet if needed
                # Example: page.click("div[data-testid='tweetButtonInline']")
            except Exception as e:
                logging.error(f"An error occurred while posting the tweet: {e}")
                return

        # Example usage: post_tweet('path/to/image.jpg')