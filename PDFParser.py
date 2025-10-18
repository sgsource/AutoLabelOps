import re
import pandas as pd
import urllib.request
import fitz  # PyMuPDF

class Planogram:
    """
    Planogram PDF parser using PyMuPDF for faster text extraction.
    Loads local or URL PDF, extracts POG number, and parses items into a DataFrame.
    """

    def __init__(self):
        self._reset()

    def _reset(self):
        """Reset internal state"""
        self.doc = None
        self.pog_df = pd.DataFrame()
        self.status_callback = lambda msg: print(msg)

    def get_pog(self, path: str, status_callback=None) -> pd.DataFrame:
        """
        Main entry point.
        path: local file path or HTTP/HTTPS URL of a PDF.
        Returns a DataFrame indexed by CRC with columns Num and UPC.
        """
        # Allow dynamic callback per call
        if status_callback:
            self.status_callback = status_callback

        try:
            self.status_callback(f"Loading PDF from {path}...")
            self._load_file(path)

            pog_num = self.get_pog_num()
            self.status_callback(f"POG number found: {pog_num}")

            self.pog_df = self._parse_data()
            self.status_callback(f"Parsed {len(self.pog_df)} items successfully.")
            return self.pog_df
        except Exception as e:
            raise RuntimeError(f"Failed to load {path}: {e}")
        finally:
            # Ensure PDF is closed after parsing to free memory
            if self.doc:
                self.doc.close()
                self._reset()

    def _load_file(self, path: str):
        """Load PDF from local path or URL"""
        if not path.lower().endswith(".pdf"):
            raise RuntimeError("Invalid file type: expected PDF.")

        if re.fullmatch(r'https?://\S+', path):
            req = urllib.request.Request(path, headers={'User-Agent': "Mozilla/5.0"})
            pdf_bytes = urllib.request.urlopen(req).read()
            self.doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        else:
            self.doc = fitz.open(path)

    def _check_doc(f):
        """Decorator to ensure doc is initialized"""
        def wrapper(self, *args, **kwargs):
            if self.doc is None:
                raise RuntimeError("PDF document not loaded")
            return f(self, *args, **kwargs)
        return wrapper

    @_check_doc
    def get_pog_num(self) -> str:
        """Extract 5-6 digit POG number from the first page"""
        text = self.doc[0].get_text()
        match = re.search(r'\b\d{5,6}\b', text)
        if match:
            return match.group(0)
        raise RuntimeError("Cannot find POG number in PDF.")

    @_check_doc
    def _parse_data(self) -> pd.DataFrame:
        """
        Parse items into a DataFrame indexed by CRC with Num and UPC columns.
        Automatically closes the document after parsing.
        """
        nums, crcs, upcs = [], [], []
        seen_nums = set()

        for page in self.doc:
            text = page.get_text()
            if not all(term in text for term in ["Loc. ID", "Status", "CRC", "Description", "Barcode"]):
                continue

            # Extract Num-CRC pairs
            matches = re.findall(r"\b(\d{1,4})\s+(\d{7})\b", text)
            # Extract 12-digit UPCs
            upc_matches = re.findall(r"\b\d{12}\b", text)

            # Filter consecutive duplicate UPCs
            last_upc = ""
            for upc in upc_matches:
                if upc != last_upc:
                    upcs.append(upc)
                    last_upc = upc

            for num, crc in matches:
                if num not in seen_nums:
                    seen_nums.add(num)
                    nums.append(num)
                    crcs.append(crc)

        df = pd.DataFrame(
            {'Num': nums, 'UPC': upcs[:len(nums)]},
            index=pd.Index(crcs, name="CRC", dtype=str)
        )

        if not df.index.is_unique:
            raise RuntimeError("Duplicate CRC codes found in PDF.")

        return df

    def get_num_items(self) -> int:
        """Return number of items parsed"""
        return 0 if self.pog_df.empty else len(self.pog_df)


# --------------------------
# CLI Test
# --------------------------
if __name__ == "__main__":
    import sys
    import time

    if __name__ == "__main__":
        if len(sys.argv) < 2:
            print("Usage: python planogram.py <PDF_PATH_OR_URL>")
            sys.exit(1)

        path = sys.argv[1]
        pog = Planogram()

        start_time = time.time()          # start timer
        df = pog.get_pog(path)
        end_time = time.time()            # end timer

        print(df)
        print(f"\nParsed {pog.get_num_items()} items in {end_time - start_time:.3f} seconds.")

