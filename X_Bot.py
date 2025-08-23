from playwright.sync_api import sync_playwright
import os
from time import sleep, time
import requests
from random import choice, randint, uniform
from dotenv import load_dotenv
import re
import logging

load_dotenv()

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[logging.StreamHandler()])

USERNAME = os.getenv('MY_USERNAME')  # replace with your environment variable for username
PASSWORD = os.getenv('MY_PASSWORD')  # replace with your environment variable for password
PROFILE_PATH = os.getenv('PROFILE_PATH')  # replace with your environment variable for profile path
CHROME_PATH = os.getenv('CHROME_PATH')  # replace with your environment variable for chrome path

with sync_playwright() as p:
    browser_type = p.chromium

    # Path to your Google Chrome installation. Modify this to point to the Chrome executable on your system.
    chrome_executable_path = CHROME_PATH

    context = browser_type.launch_persistent_context(
        executable_path=chrome_executable_path,
        user_data_dir=PROFILE_PATH,
        headless=False,
    )

    page = context.new_page()


    def post_text_tweet(text):
        try:
            page.goto("https://twitter.com/compose/tweet")
            sleep(uniform(5, 10))
            # Wait for the tweet box to be available
            page.wait_for_selector("div[data-testid='tweetTextarea_0']", timeout=15000)
            page.fill("div[data-testid='tweetTextarea_0']", text)
            sleep(uniform(2, 4))

            # Try multiple ways to find and click the Post button
            selectors = [
                "div[data-testid='toolBar'] button[data-testid='tweetButtonInline']",  # usual
                "button[data-testid='tweetButtonInline']",  # fallback
                "div[role='button'][data-testid='tweetButtonInline']",  # fallback
                "button:has-text('Post')",  # visible text
            ]
            post_clicked = False
            for selector in selectors:
                try:
                    button = page.query_selector(selector)
                    if button:
                        # Scroll into view and check enabled state
                        button.scroll_into_view_if_needed()
                        sleep(1)
                        if button.is_enabled():
                            button.click()
                            logging.info(f"Clicked Post button using selector: {selector}")
                            post_clicked = True
                            break
                        else:
                            logging.warning(f"Post button found but not enabled: {selector}")
                except Exception as e:
                    logging.warning(f"Failed to click Post button with selector {selector}: {e}")
            if not post_clicked:
                logging.error("Could not find or click the Post button. Please check selector or UI changes.")
            else:
                sleep(2)
                logging.info("Posted text tweet successfully.")
        except Exception as e:
            logging.error(f"An error occurred while posting the text tweet: {e}")



    def fetch_text_from_perplexity():
        api_key = os.getenv('PERPLEXITY_API_KEY')
        prompt = os.getenv('PROMPT')
        url = "https://api.perplexity.ai/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": "sonar-pro",
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }
        try:
            response = requests.post(url, headers=headers, json=data)
            if response.status_code != 200:
                logging.error(f"Perplexity API error {response.status_code}: {response.text}")
                response.raise_for_status()
            result = response.json()
            # Extract the text from the response
            return result['choices'][0]['message']['content']
        except Exception as e:
            logging.error(f"Failed to fetch text from Perplexity: {e}")
            return None

    def follow():
        follow_id_list = []  # Replace with your list of usernames

        try:
            random_number = choice(range(len(follow_id_list)))
            page.goto(f"https://twitter.com/{follow_id_list[random_number]}/followers")
            sleep(uniform(5, 10))
        except Exception as e:
            logging.error(f"Error navigating to the followers page: {e}")
            return

        try:
            # Get all the follow buttons
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
            # Navigate to the following page
            page.goto("https://twitter.com/@/following")
            sleep(uniform(5, 10))
        except Exception as e:
            logging.error(f"Error navigating to the following page: {e}")
            return

        try:
            # Get all the unfollow buttons
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


    # Start the script
    script_start_time = time()  # To keep track of when the script started
    MAX_LOGIN_ATTEMPTS = 3

    while True:  # Infinite loop to ensure the script runs indefinitely

        page.goto("https://twitter.com/home")
        sleep(uniform(5, 10))

        # Check if need to login
        if "/i/flow/login" in page.url or "/?logout" in page.url:
            login_attempts = 0

            while login_attempts < MAX_LOGIN_ATTEMPTS:
                try:
                    page.fill("input[name='text']", USERNAME)
                    sleep(uniform(2, 5))
                    page.click("span:has-text('Next')")
                    sleep(uniform(2, 5))

                    # Check for verification step (email/phone)
                    if page.is_visible("input[name='text']") and page.is_visible("span:has-text('Next')"):
                        VERIFICATION_EMAIL = os.getenv('VERIFICATION_EMAIL')
                        page.fill("input[name='text']", VERIFICATION_EMAIL)
                        sleep(uniform(2, 4))
                        page.click("span:has-text('Next')")
                        sleep(uniform(2, 4))

                    # Check for password step
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
                break

        # Define the total number of posts to make in the day
        num_of_posts_today = randint(4, 6)

        # Define the number of times to run the follow() function
        follow_times_today = randint(0, 3)
        follow_intervals = sorted([randint(0, 86400) for _ in range(follow_times_today)])
        next_follow_index = 0  # To keep track of which follow_interval to check next

        # Calculate the average interval
        avg_interval = 86400 / num_of_posts_today

        # Define the time we start the loop, to make sure we don't cross into the next day
        start_time = time()


        while num_of_posts_today > 0 and (time() - start_time) < 86400:
            # Fetch text from Perplexity and post as tweet
            text = fetch_text_from_perplexity()
            if text:
                post_text_tweet(text)
            else:
                logging.error("No text fetched from Perplexity.")

            # Commented out image/video posting
            # media_type = fetchPost()
            # if media_type == 'image':
            #     post_tweet('image.jpg')
            #     os.remove('image.jpg')  # Delete the image after posting
            # elif media_type == 'video':
            #     post_tweet('video.mp4')
            #     os.remove('video.mp4')  # Delete the video after posting

            # Check if it's time for the next follow action
            if next_follow_index < len(follow_intervals) and (time() - start_time) > follow_intervals[next_follow_index]:
                follow()
                next_follow_index += 1

            # Randomize the sleep time based on the average interval with ±20% variation
            sleep_time = randint(int(0.8 * avg_interval), int(1.2 * avg_interval))
            sleep(sleep_time)

            num_of_posts_today -= 1

        # Check if a week has passed to unfollow
        if time() - script_start_time >= 7 * 86400:
            unfollow()
            script_start_time = time()  # Reset the timer after unfollowing

        # Sleep until the next day starts
        while (time() - start_time) < 86400:
            sleep(600)  # Sleep for 10 minutes and then check again