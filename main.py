#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Automate login to an authorized pfSense captive portal."""

import os
import sys
import time

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException, WebDriverException

# Configuration
USERNAME = os.getenv("PFSENSE_USERNAME", "")
PASSWORD = os.getenv("PFSENSE_PASSWORD", "")
URL = os.getenv("PFSENSE_URL", "")
HEADLESS = os.getenv("PFSENSE_HEADLESS", "true").lower() in {"1", "true", "yes"}
CHROME_PATH = os.getenv("CHROME_PATH", "")
CHROMEDRIVER_PATH = os.getenv("CHROMEDRIVER_PATH", "")
TIMEOUT = int(os.getenv("PFSENSE_TIMEOUT", "20"))

# ANSI color codes for CLI output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def colored_print(text, color=Colors.ENDC):
    """
    Prints text to the console with the specified color.

    Args:
        text (str): The text to print.
        color (str, optional): The color code to use. Defaults to Colors.ENDC (no color).
    """
    print(f"{color}{text}{Colors.ENDC}")

def login_to_captive_portal(url, username, password, headless=True):
    """
    Logs in to a captive portal.

    Args:
        url (str): The URL of the captive portal login page.
        username (str): The username for the captive portal.
        password (str): The password for the captive portal.
        headless (bool, optional): Whether to run the browser in headless mode. Defaults to True.

    Returns:
        bool: True if login was successful, False otherwise.
    """
    options = Options()
    if headless:
        options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
    if CHROME_PATH:
        options.binary_location = CHROME_PATH

    service = Service(executable_path=CHROMEDRIVER_PATH) if CHROMEDRIVER_PATH else Service()
    driver = None
    try:
        driver = webdriver.Chrome(service=service, options=options)
        driver.get(url)
        colored_print(f"Navigated to: {url}", Colors.OKBLUE)

        wait = WebDriverWait(driver, TIMEOUT)
        username_field = wait.until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "#auth_user, [name='auth_user'], #username, [name='username']")
            )
        )
        password_field = wait.until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "#auth_pass, [name='auth_pass'], #password, [name='password']")
            )
        )
        submit_button = wait.until(
            EC.element_to_be_clickable(
                (By.CSS_SELECTOR, "button[type='submit'], input[type='submit'], button")
            )
        )
    except WebDriverException as e:
        colored_print(f"Error: Could not open or inspect the captive portal: {e}", Colors.FAIL)
        return False
    try:
        username_field.clear()
        password_field.clear()
        username_field.send_keys(username)
        password_field.send_keys(password)
        submit_button.click()
        colored_print("Submitted the captive portal form.", Colors.OKBLUE)

        def login_form_is_gone(current_driver):
            return not current_driver.find_elements(
                By.CSS_SELECTOR,
                "#auth_user, [name='auth_user'], #username, [name='username']",
            )

        try:
            wait.until(login_form_is_gone)
        except TimeoutException:
            colored_print("Login failed: the portal still shows its login form.", Colors.FAIL)
            return False

        colored_print("Login successful: the portal login form disappeared.", Colors.OKGREEN)
        return True
    except WebDriverException as e:
        colored_print(f"Error while submitting the captive portal form: {e}", Colors.FAIL)
        return False
    finally:
        if driver is not None:
            driver.quit()

def main():
    """
    Main function to run the captive portal login script.
    """
    retries = 3
    delay = 5

    missing = [name for name, value in {
        "PFSENSE_URL": URL,
        "PFSENSE_USERNAME": USERNAME,
        "PFSENSE_PASSWORD": PASSWORD,
    }.items() if not value]
    if missing:
        colored_print(f"Error: configure these environment variables: {', '.join(missing)}", Colors.FAIL)
        return 2

    for attempt in range(retries):
        colored_print(f"Attempt {attempt + 1} to login to captive portal at {URL}", Colors.OKBLUE)
        success = login_to_captive_portal(URL, USERNAME, PASSWORD, HEADLESS)
        if success:
            colored_print("Successfully logged in to the captive portal.", Colors.OKGREEN)
            return 0
        else:
            colored_print(f"Login failed.  Retrying in {delay} seconds...", Colors.WARNING)
            time.sleep(delay)
    colored_print("Failed to login to the captive portal after multiple attempts.", Colors.FAIL)
    return 1

if __name__ == "__main__":
    sys.exit(main())
