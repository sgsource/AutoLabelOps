import pathlib
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import TimeoutException
import time
import pandas as pd

from DriverManager import DriverManager

class Telxon:
    SELECTORS = {
        "login_button": "B5975482935189201124",
        "username": "P9000_USERNAME",
        "password": "P9000_PASSWORD",
        "sign_in": "B3766789551193137132",
    }

    def __init__(self):
        self.telxon_url = (
            'https://prodasapapp1.aafes.com:7002/ords/'
            'ftmeade/f?p=ASAP_HH_BASE:LOGIN_DESKTOP:0::::P9999_EXCHANGE,P9999_PATH_VAR:FTMEADE,BETABASE'
        )
        # discard DriverManager
        # driver must persist in between functions
        self.driver = None

    @staticmethod
    def _click_link(driver, ul_id, li_index, verbose=False):
        """Click <a> inside <ul> by index"""
        ul_element = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.ID, ul_id))
        )
        # ul_element = driver.find_element(By.ID, ul_id)
        li_elements = ul_element.find_elements(By.TAG_NAME, "li")
        if verbose:
            for li in li_elements:
                print(f"li: {li.text}")
        li_elements[li_index].find_element(By.TAG_NAME, "a").click()

    def _fill_input_by_id(self, id: str, text: str, enter=False):
        input_field = self.driver.find_element(By.ID, id)
        input_field.send_keys(text)
        if enter:
            input_field.send_keys(Keys.ENTER)

    @staticmethod
    def _select_by_index(driver, id: str, index: int):
        try:
            dropdown = WebDriverWait(driver, 10).until(
                EC.visibility_of_element_located((By.ID, id))
            )
            Select(dropdown).select_by_index(index)
        except Exception as e:
            raise e
        
    def _wait_to_find(self, o, pair):
        return o.EC.visibility_of_element_located(pair)

    """
    Step 2
    Block other threads from downloading
    """
    def download(self, lan_id, visibility=False, status_callback=None):
        driver = self.driver

        # Click the submit button (I assume you want to click it, not just find it)
        WebDriverWait(driver, 10, poll_frequency=0.15).until(
            EC.element_to_be_clickable((By.ID, 'B4986078001920273596'))
        ).click()

        submit_msg = WebDriverWait(driver, 15, poll_frequency=0.15).until(
            EC.visibility_of_element_located((By.XPATH, "//p[contains(text(), 'has been scheduled for delivery to machine')]"))
        )
        print_id = submit_msg.text[12:18]

        # Then continue with going to email etc
        driver.get('https://outlook.office365.com/mail/')

        # Sign in
        email_input = WebDriverWait(driver, 20).until(
            EC.visibility_of_element_located((By.ID, 'i0116'))
        )
        email_input.send_keys(f'{lan_id}@aafes.com')
        WebDriverWait(driver, 20, poll_frequency=0.15).until(
            EC.element_to_be_clickable((By.ID, 'idSIButton9'))
        ).click()
        # driver.find_element(By.ID, 'idSIButton9').click()

        # must click entry, no preview.
        mail_entry = WebDriverWait(driver, 20, poll_frequency=0.15).until(
            EC.element_to_be_clickable((By.XPATH, f"//*[contains(@aria-label, 'Has attachments machine PCL Report from ASAP PMrpt{print_id}')]"))
        )
        # aria-label="Has attachments machine PCL Report from ASAP PMrpt020683 7:38 AM No preview is available."
        # PCL Report from ASAP PMrpt020683

        mail_entry.click()

        WebDriverWait(driver, 20, poll_frequency=0.15).until(
            EC.element_to_be_clickable((By.XPATH, f"//div[@title='PMrpt{print_id}.pdf']"))
        ).click()

        WebDriverWait(driver, 20, poll_frequency=0.15).until(
            EC.element_to_be_clickable((By.XPATH, "//span[text()='Download']"))
        ).click()

        time.sleep(2)

        # teardown
        self.driver.quit()
        self.driver = None

        filename = f'PMrpt{print_id}.pdf'

        return self._get_full_path(filename)
    
    def _get_full_path(self, filename: str):
        home_directory = pathlib.Path.home()
        downloads_path = home_directory / "Downloads"
        return str(downloads_path / filename)

    """
    Step 1
    Bottleneck
    """
    def scan_labels(self, subset, inches, creds, visibility=False, status_callback=None):
        yid, pwd = creds

        def update_status(msg):
            if status_callback:
                status_callback(msg)
            else:
                print(msg)

        # Set up persistent driver
        if visibility:
            self.driver = webdriver.Chrome()
        else:
            options = webdriver.ChromeOptions()
            options.add_argument("--headless=new")
            options.add_argument("--disable-gpu")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            self.driver = webdriver.Chrome(options=options)

        driver = self.driver
        wait = WebDriverWait(driver, 15, poll_frequency=0.15)

        driver.get(self.telxon_url)
        update_status("Navigating to login...")

        # Login
        try:
            wait.until(EC.element_to_be_clickable((By.ID, self.SELECTORS["login_button"]))).click()
            driver.find_element(By.ID, self.SELECTORS["username"]).send_keys(f"y{yid}")
            driver.find_element(By.ID, self.SELECTORS["password"]).send_keys(pwd)
            driver.find_element(By.ID, self.SELECTORS["sign_in"]).click()
        except Exception as e:
            update_status(f"Login failed: {e}")
            return

        # Navigate to scan labels
        NAV_TO_SCAN_LABELS = [
            ('3763435963668262110', 2),
            ('5702700700995105695', 1),
        ]
        for ul_id, li_index in NAV_TO_SCAN_LABELS:
            try:
                self._click_link(driver, ul_id, li_index)
            except Exception as e:
                update_status(f"Navigation failed at {ul_id}[{li_index}]: {e}")
                return

        # Label batch description
        try:
            self._fill_input_by_id('P127_BATCH_DESC', 'AutoLabelOps')

            if inches == 1:
                self._select_by_index(driver, 'P127_SHELF_LABEL_ID', 2)

            self._select_by_index(driver, 'P127_PRINT_PRICE_INDCT', 1)

            # Submit label settings
            driver.find_element(By.ID, 'B4986085331857273610').click()

            # Wait for lookup dropdown before continuing
            wait.until(EC.presence_of_element_located((By.ID, 'P127_LOOKUP_TYPE')))
            self._select_by_index(driver, 'P127_LOOKUP_TYPE', 1)

        except Exception as e:
            update_status(f"Form fill error: {e}")
            return

        # Scan each item
        for i, crc in enumerate(subset.index.to_list()):
            try:
                self._fill_input_by_id('P127_LOOKUP_NBR', crc, enter=True)

                info_element = wait.until(
                    EC.visibility_of_element_located((By.ID, 'P127_INFO'))
                )
                update_status(f'================\n{info_element.text}')

                # Confirm label was added
                wait.until(
                    EC.text_to_be_present_in_element(
                        (By.ID, 'P127_INFO_CONTAINER'),
                        f'{i + 1} LABELS IN LIST'
                    )
                )
            except TimeoutException:
                update_status(f"Timeout: {crc}#{subset.loc[crc, 'Num']} skipped.")
            except Exception as e:
                update_status(f"Error with {crc}: {e}")

        update_status("Scanning complete.")


        # Telxon left hanging

# --------------------------
# CLI Test
# --------------------------
if __name__ == "__main__":
    import sys
    import time
    import os
    import fitz

    if __name__ == "__main__":
        o = Telxon()
        data = {
            '1549593': { "Num": 1 },
            '3841822': { "Num": 2 },
            '1549428': { "Num": 3 },
            '6314524': { "Num": 4 },
        }
        df = pd.DataFrame.from_dict(data, orient='index')
        vis = False
        o.scan_labels(df, 2, ('543697', 'Iiop890'), vis)
        filepath = o.download('ohso', vis)
        print(filepath)

        # # Open the generated PDF cross-platform
        # outfile_path = os.path.abspath("numbered_labels.pdf")
        # try:
        #     if sys.platform.startswith("win"):
        #         os.startfile(outfile_path)
        #     elif sys.platform.startswith("darwin"):
        #         subprocess.Popen(["open", outfile_path])
        #     else:  # Linux
        #         subprocess.Popen(["xdg-open", outfile_path])
        #     self.status_label.setText("Labels generated and opened. Closing app...")
        # except Exception as e:
        #     self.status_label.setText("Failed to open PDF")