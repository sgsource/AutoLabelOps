from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from DriverManager import DriverManager

def get_pog_links(pog_num: str, visible=False, status_callback=None) -> list[tuple[str, str]]:
    """Return list of (size, href) for given POG number and emit status messages."""
    def update_status(msg):
        if status_callback:
            status_callback(msg)
        else:
            print(msg)            

    if not pog_num.isdigit():
        raise ValueError("POG number must be numeric")

    update_status(f"Searching all sizes of {pog_num}...")

    size_href_pairs = []

    URL = "https://h5.aafes.com/POG/Search/ByPlanogram"

    with DriverManager(visible=visible) as driver:
        driver.get(URL)

        driver.find_element(By.ID, "mp_num").send_keys(pog_num)
        driver.find_element(By.NAME, "SubmitButton").click()

        table = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "table"))
        )
        rows = table.find_elements(By.TAG_NAME, "tr")
        for idx, row in enumerate(rows[1:], start=1):
            tds = row.find_elements(By.TAG_NAME, "td")
            if len(tds) < 3:
                continue
            size = tds[2].text.strip()
            links = row.find_elements(By.TAG_NAME, "a")
            
            for link in links[::2]:
                href = link.get_attribute("href")
                update_status(f"Found {href} POG PDF links.")
                size_href_pairs.append((size, href))

        update_status(f"Found {len(size_href_pairs)} POG PDF links.")

    return size_href_pairs

def level_of(link):
    import re
    match = re.search(r'id=\d{5,6}l(\d{1,2}).pdf', link)
    return match.group(1)

# --------------------------
# CLI Test
# --------------------------
if __name__ == "__main__":
    import sys
    import time

    if __name__ == "__main__":
        if len(sys.argv) < 2:
            print("Usage: python POGSearch.py <PDF_PATH_OR_URL>")
            sys.exit(1)

        num = sys.argv[1]
        get_pog_links(num)
