from selenium import webdriver
from selenium.webdriver.chrome.options import Options

class DriverManager:
    """Context manager for automatic Chrome WebDriver creation and cleanup."""
    def __init__(self, visible=False):
        self.visible = visible
        self.driver = None

    def __enter__(self):
        options = Options()
        if not self.visible:
            options.add_argument("--headless=new")
        self.driver = webdriver.Chrome(options=options)
        self.driver.implicitly_wait(10)
        return self.driver

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.driver:
            self.driver.quit()
