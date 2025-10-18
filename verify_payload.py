import json, base64
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes, serialization
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import WebDriverException

def verify_payload():
    url = "https://singular-snickerdoodle-de09f9.netlify.app/payload.json"
    try:
        options = webdriver.ChromeOptions()
        options.add_argument("--headless=new") 

        driver = webdriver.Chrome(options=options)
        driver.get(url)

        pre_element = driver.find_element(By.TAG_NAME, 'pre')
        json_content = pre_element.text
        data = json.loads(json_content)

        payload_bytes = base64.b64decode(data["payload"])
        signature = base64.b64decode(data["sig"])

        public_key_pem = b"""-----BEGIN PUBLIC KEY-----
MFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAEdoUvlLjynhTV+MUNR6MhuBofhAfV
tzviR3OO8ugwD2m1V28R8NxJfhDrf76q36Fn4wCN7WSMDmbTfKB8/hB08A==
-----END PUBLIC KEY-----"""

        public_key = serialization.load_pem_public_key(public_key_pem)
        public_key.verify(signature, payload_bytes, ec.ECDSA(hashes.SHA256()))

        payload = json.loads(payload_bytes)

        _ = payload.get("allow", False)

        return True, ''
    except WebDriverException as e:
        # if url is no longer accessible
        return False, "Cannot verify app validity. App will exit."
    except Exception:
        # this should never really happen. public key should always be valid.
        return False, "Signature verification failed! App will exit."
    finally:
        driver.quit()