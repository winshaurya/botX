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
PROFILE_PATH = os.getenv('PROFILE_PATH', '/home/runner/work/botX/profile')
CHROME_PATH = os.getenv('CHROME_PATH', '/usr/bin/chromium-browser')
PERPLEXITY_API_KEY = os.getenv('PERPLEXITY_API_KEY')
PERPLEXITY_API_URL = "https://api.perplexity.ai/chat/completions"  # Updated endpoint per docs

with sync_playwright() as p:
    browser_type = p.chromium

    # Path to your Google Chrome installation. Modify this to point to the Chrome executable on your system.
    chrome_executable_path = CHROME_PATH

    context = browser_type.launch_persistent_context(
        user_data_dir=PROFILE_PATH,
        headless=False,
    )

    page = context.new_page()


    def post_tweet(file_path):
        try:
            # Navigate to the home page (new UI)
            page.goto("https://x.com/home")
            sleep(uniform(5, 10))
        except Exception as e:
            logging.error(f"An error occurred while navigating to the post page: {e}")
            return
        try:
            # Will post with the given file path
            if not os.path.exists(file_path):
                logging.error(f"The file {file_path} does not exist.")
                return
            page.set_input_files("input[data-testid='fileInput']", file_path)
            sleep(uniform(15, 20))
            post_button = page.wait_for_selector("button[data-testid='tweetButtonInline']", timeout=10000)
            for _ in range(10):
                if post_button.is_enabled():
                    post_button.click()
                    sleep(uniform(3, 6))
                    break
                sleep(1)
            else:
                logging.error("Post button found but never enabled.")
        except Exception as e:
            logging.error(f"An error occurred while posting the tweet: {e}")

    def post_text_tweet(text):
        try:
            page.goto("https://x.com/home")
            sleep(uniform(5, 10))
            # Focus and type in the rich text input container (new UI)
            tweet_box = page.wait_for_selector("div[data-testid='tweetTextarea_0']", timeout=10000)
            tweet_box.click()
            page.keyboard.type(text)
            sleep(uniform(2, 4))
            post_button = page.wait_for_selector("button[data-testid='tweetButtonInline']", timeout=10000)
            for _ in range(10):
                if post_button.is_enabled():
                    post_button.click()
                    sleep(uniform(3, 6))
                    break
                sleep(1)
            else:
                logging.error("Post button found but never enabled.")
        except Exception as e:
            logging.error(f"Error posting text tweet: {e}")

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


    def fetchPost():
        # Number of attempts to fetch a post
        max_attempts = 10
        attempts = 0

        # List of sources to fetch posts from, replace with your list of sources
        sources = [
        ]


        while attempts < max_attempts:
            try:
                source, randint_range = choice(sources)
                url = f"{source}{randint(*randint_range)}?embed=1&mode=tme"

                page.goto(url)
                sleep(uniform(5, 10))

                # Check for image
                picElement = page.query_selector('a.tgme_widget_message_photo_wrap')
                if picElement:
                    imageStyle = picElement.get_attribute('style')
                    regexPattern = r"background-image:url\('(.*)'\)"
                    match = re.search(regexPattern, imageStyle)

                    if match:
                        response = requests.get(match.group(1))
                        if response.status_code == 200:
                            with open('image.jpg', 'wb') as file:
                                file.write(response.content)
                            return 'image'
                        else:
                            logging.error('Failed to download the image')
                            return None

                # Check for video
                videoElement = page.query_selector('video.tgme_widget_message_video.js-message_video')
                if videoElement:
                    videoURL = videoElement.get_attribute('src')
                    if videoURL:
                        response = requests.get(videoURL)
                        if response.status_code == 200:
                            with open('video.mp4', 'wb') as file:
                                file.write(response.content)
                            return 'video'
                        else:
                            logging.error('Failed to download the video')
                            return None

                attempts += 1

            except Exception as e:
                logging.error(f"Attempt {attempts + 1} failed with error: {e}")
                attempts += 1

        logging.error("Failed to fetch a post after 3 attempts.")
        return None

    ## def follow():
    ##     follow_id_list = []  # Replace with your list of usernames
    ##
    ##     try:
    ##         random_number = choice(range(len(follow_id_list)))
    ##         page.goto(f"https://twitter.com/{follow_id_list[random_number]}/followers")
    ##         sleep(uniform(5, 10))
    ##     except Exception as e:
    ##         logging.error(f"Error navigating to the followers page: {e}")
    ##         return
    ##
    ##     try:
    ##         # Get all the follow buttons
    ##         follow_buttons = page.query_selector_all("button[aria-label^='Follow @'][role='button']")
    ##         if not follow_buttons:
    ##             logging.error("No follow buttons found on the page.")
    ##             return
    ##
    ##         num_to_follow = randint(1, min(15, len(follow_buttons)))
    ##     except Exception as e:
    ##         logging.error(f"Error querying the follow buttons: {e}")
    ##         return
    ##
    ##     followed_count = 0  # To keep track of the number of successful follows
    ##
    ##     # Follow random number of accounts
    ##     for button in range(num_to_follow):
    ##         try:
    ##             follow_buttons[button].click()
    ##             sleep(uniform(2, 5))
    ##             followed_count += 1
    ##         except Exception as e:
    ##             logging.error(f"Error following account number {button + 1}: {e}")
    ##
    ##     logging.info(f"Followed {followed_count} accounts.")

    ## def unfollow():
    ##     try:
    ##         # Navigate to the following page
    ##         page.goto("https://twitter.com/@/following")
    ##         sleep(uniform(5, 10))
    ##     except Exception as e:
    ##         logging.error(f"Error navigating to the following page: {e}")
    ##         return
    ##
    ##     try:
    ##         # Get all the unfollow buttons
    ##         unfollow_buttons = page.query_selector_all("button[role='button'][aria-label^='Following @']")
    ##         if not unfollow_buttons:
    ##             logging.error("No unfollow buttons found on the page.")
    ##             return
    ##
    ##         num_to_unfollow = randint(5, min(10, len(unfollow_buttons)))
    ##     except Exception as e:
    ##         logging.error(f"Error querying the unfollow buttons: {e}")
    ##         return
    ##
    ##     unfollowed_count = 0  # To keep track of the number of successful unfollows
    ##
    ##     # Unfollow a random number of accounts
    ##     for button in range(num_to_unfollow):
    ##         try:
    ##             unfollow_buttons[button].click()
    ##             sleep(uniform(2, 3))
    ##             page.wait_for_selector("button[role='button'] span:has-text('Unfollow')").click()
    ##             sleep(uniform(2, 5))
    ##             unfollowed_count += 1
    ##         except Exception as e:
    ##             logging.error(f"Error unfollowing account number {button + 1}: {e}")
    ##
    ##     logging.info(f"Unfollowed {unfollowed_count} accounts.")


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
                    page.wait_for_selector("input[name='password']").fill(PASSWORD)
                    sleep(uniform(2, 5))
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
    # follow_times_today = randint(0, 3)
    # follow_intervals = sorted([randint(0, 86400) for _ in range(follow_times_today)])
    # next_follow_index = 0

        avg_interval = 86400 / num_of_posts_today
        start_time = time()

        while num_of_posts_today > 0 and (time() - start_time) < 86400:
            # --- Perplexity API call and tweet ---
            prompt = "Write a motivational quote for Twitter."
            answer = get_perplexity_answer(prompt)
            if answer:
                post_text_tweet(answer)
                logging.info(f"Tweeted Perplexity answer: {answer}")

            # # --- Existing media tweet logic ---
            # media_type = fetchPost()
            # if media_type == 'image':
            #     post_tweet('image.jpg')
            #     os.remove('image.jpg')
            # elif media_type == 'video':
            #     post_tweet('video.mp4')
            #     os.remove('video.mp4')

            # # Check if it's time for the next follow action
            # # if next_follow_index < len(follow_intervals) and (time() - start_time) > follow_intervals[next_follow_index]:
            # #     follow()
            #     next_follow_index += 1

            sleep_time = randint(int(0.8 * avg_interval), int(1.2 * avg_interval))
            sleep(sleep_time)
            num_of_posts_today -= 1

    # if time() - script_start_time >= 7 * 86400:
    #     unfollow()
    #     script_start_time = time()

        while (time() - start_time) < 86400:
            sleep(600)