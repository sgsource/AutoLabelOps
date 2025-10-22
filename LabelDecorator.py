import fitz
import PDFParser
import pandas as pd
import re
import math
import sys

GREEN = '\033[92m'
RED = '\033[31m'
CYAN = '\033[96m'
RESET = '\033[0m'

class Label:
    def __init__(self, label_sheet : str, inches : int, res = 20):
        self.inches = inches

        if inches == 2:
            self.label_capacity = 20
        elif inches == 1:
            self.label_capacity = 32
        else:
            raise ValueError(f"{inches} in. labels not supported")
        
        self.label_sheet = label_sheet

        self.df = pd.DataFrame(columns=['seq'])

        self.pog = None

        self.res = res

    def __str__(self):
        return f"{self.inches} in. Label object"
    
    def assoc_pog(self, pog, verbose=True):
        self.pog = pog
    
    # util methods (not called)
    def get_points(self, pos : int):
        if self.inches == 2:
            x, y = 105, 37.5
            w, h = (515 - 105) / 2, (760 - 110) / 9 # ref numbers. eyeballed and handtested

            dx = (pos - 1) % 2
            dy = ((pos - 1) // 2) % 10 # // is floor (truncates)

            x0 = x + dx * w
            y0 = y + dy * h
            x1 = x + (dx + 1) * w
            y1 = y + (dy + 1) * h
        elif self.inches == 1:
            x, y = 57.5, 37.5
            w, h = (562.5 - x) / 4, (757.5 - y) / 8

            dx = (pos - 1) % 4
            dy = ((pos - 1) // 4) % 8 # // is floor (truncates)

            x0 = x + dx * w
            y0 = y + dy * h
            x1 = x + (dx + 1) * w
            y1 = y + (dy + 1) * h
        else:
            raise ValueError(f"{self.inches} not supported")
        return x0, y0, x1, y1

    def cut(self, page, pos : int):
        mat = fitz.Matrix(self.res, self.res)

        x0, y0, x1, y1 = self.get_points(pos)
        clip_rect = fitz.Rect(x0, y0, x1, y1)
        
        return page.get_pixmap(matrix=mat, clip=clip_rect)
    
    def paste(self, page, pos : int, pixmap):
        x0, y0, x1, y1 = self.get_points(pos)
        rect = fitz.Rect(x0, y0, x1, y1)
        page.insert_image(rect, pixmap=pixmap)

    def put_number(self, page, pos : int, num : int):
        _, y0, x1, _ = self.get_points(pos)

        dx = 25 if self.inches == 2 else 25
        dy = 25 if self.inches == 2 else 35

        top_right_pt = fitz.Point(x1 - dx, y0 + dy)
        page.insert_text(top_right_pt, str(num))

    # must be called
    def get_crc_seq(self):
        seq = 1
        doc = fitz.open(self.label_sheet)
        for page in doc:
            text = page.get_text()
            matches = re.findall(r"  \d{7}", text)
            for crc_str in matches:
                crc = crc_str.strip()
                self.df.loc[crc, 'seq'] = seq
                seq += 1
        doc.close()
        print(f"CRC sequence collected for {GREEN}{len(self.df)}{RESET} items.")

    def collect_labels(self):
        doc = fitz.open(self.label_sheet)

        for crc, row in self.df.iterrows():
            seq = row['seq']
            pno = (seq - 1) // self.label_capacity
            page = doc[pno]

            pos = seq % self.label_capacity
            pixmap = self.cut(page, pos)
            self.df.loc[crc, 'pixmap'] = pixmap

        print(f"Collected all labels.")
        return self.df

    def decorate_labels(self, pog_df: pd.DataFrame, outfile = "numbered_labels", verbose=False):
        doc = fitz.open(self.label_sheet)

        for crc, row in self.df.iterrows():
            seq = row['seq']
            pno = (seq - 1) // self.label_capacity
            if verbose:
                print(f"pno: {pno}, num: {seq}, cap: {self.label_capacity}")
            pos = seq % self.label_capacity

            page = doc[pno]

            num = "NP"
            if crc in pog_df.index:
                num = pog_df.loc[crc, 'Num']
            self.put_number(page, pos, num)
        
        doc.save(f"{outfile}.pdf")
        doc.close()