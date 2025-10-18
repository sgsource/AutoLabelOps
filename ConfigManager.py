import json
import os
from cryptography.fernet import Fernet

class ConfigManager:
    def __init__(self, key=None, config_path="config.json"):
        self.config_path = config_path
        # Fixed key (embed a secret key or pass in)
        if key is None:
            key = b"uHhP5m_0sZXYM1sA0kp8v6zH8Ujv06iB-SUgN9f9i8g="
        self._fernet = Fernet(key)

    def set(self, key, value):
        """Encrypt value and save to config.json, create file if missing"""
        data = {}
        if os.path.isfile(self.config_path):
            try:
                with open(self.config_path, "r") as f:
                    encrypted_data = json.load(f)
                # decrypt existing entries
                for k, v in encrypted_data.items():
                    data[k] = self._fernet.decrypt(v.encode()).decode()
            except Exception:
                pass  # ignore if decryption fails
        data[key] = value
        # re-encrypt everything
        encrypted_data = {k: self._fernet.encrypt(v.encode()).decode() for k, v in data.items()}
        with open(self.config_path, "w") as f:
            json.dump(encrypted_data, f)

    def get(self, key):
        """Return decrypted value, or False if file/key missing"""
        if not os.path.isfile(self.config_path):
            return False
        try:
            with open(self.config_path, "r") as f:
                encrypted_data = json.load(f)
            if key not in encrypted_data:
                return False
            return self._fernet.decrypt(encrypted_data[key].encode()).decode()
        except Exception:
            return False