from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from DriverManager import DriverManager

class Telxon:
    """
    Selenium automation for Telxon web interface.
    WebDriver is automatically created and destroyed per operation.
    """

    SELECTORS = {
        "login_button": "B5975482935189201124",
        "username": "P9000_USERNAME",
        "password": "P9000_PASSWORD",
        "sign_in": "B3766789551193137132",
        "pog_input": "P36_POG_NUM",
        "pog_submit": "B6172940163361321969",
        "level_input": "P26_LEVEL_ID",
    }

    NAVIGATION_STEPS = [
        ("3763435963668262110", 3),  # Item Management
        ("6147166050736792236", 9),
        ("6152138399588205344", 2),  # POGS
    ]

    def __init__(self):
        self.start_url = (
            "https://prodasapapp1.aafes.com:7002/ords/ftmeade/f?"
            "p=ASAP_HH_BASE:LOGIN_DESKTOP:0::::P9999_EXCHANGE,P9999_PATH_VAR:FTMEADE,BETABASE"
        )

    def get_level(self, pog_num: str, credentials, visibility=False, verbose=False, status_callback=None):
        """
        Log into Telxon, navigate to POG, and return Level ID.
        Emits status messages to status_callback if provided.
        """
        yid, pwd = credentials
        level = None

        def update_status(msg):
            if status_callback:
                status_callback(msg)
            elif verbose:
                print(msg)

        update_status("Fetching Level ID...")

        with DriverManager(visible=visibility) as driver:
            driver.get(self.start_url)

            # Login
            WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.ID, self.SELECTORS["login_button"]))
            ).click()
            driver.find_element(By.ID, self.SELECTORS["username"]).send_keys(f"y{yid}")
            driver.find_element(By.ID, self.SELECTORS["password"]).send_keys(pwd)
            driver.find_element(By.ID, self.SELECTORS["sign_in"]).click()

            # Navigation
            for ul_id, li_index in self.NAVIGATION_STEPS:
                self._click_link(driver, ul_id, li_index, verbose)

            # POG input
            pog_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, self.SELECTORS["pog_input"]))
            )
            pog_input.clear()
            pog_input.send_keys(pog_num)
            pog_input.send_keys(Keys.ENTER)

            WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.ID, self.SELECTORS["pog_submit"]))
            ).click()

            # Get level
            level_elem = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, self.SELECTORS["level_input"]))
            )
            level = level_elem.get_attribute("value")
            update_status(f"Level ID acquired: {level}")

        return level


    @staticmethod
    def _click_link(driver, ul_id, li_index, verbose=False):
        """Click <a> inside <ul> by index"""
        ul_element = driver.find_element(By.ID, ul_id)
        li_elements = ul_element.find_elements(By.TAG_NAME, "li")
        if verbose:
            for li in li_elements:
                print(f"li: {li.text}")
        li_elements[li_index].find_element(By.TAG_NAME, "a").click()

    def _navigate_to_pogs(self, driver, verbose=False):
        """Combined navigation steps to POGS"""
        for ul_id, li_index in self.NAVIGATION_STEPS:
            self._click_link(driver, ul_id, li_index, verbose)
