import os
import re
import requests
from bs4 import BeautifulSoup

from entities.utils.rare import mGenerateProjectId
from entities.utils.sql import SQLRetriever
from entities.utils.files import mGetDBDConfig, mGetFile
from log.logger import mLogInfo, mLogError

class DBDScraper:
    """Handles fetching and parsing data from the Dead by Daylight Wiki and updating the local database."""
    def __init__(self, url: str = "https://deadbydaylight.wiki.gg/api.php?action=parse&page=Perks&format=json"):
        self.url = url
        self.headers = {
            "User-Agent": "UltraBot/2.0 WebScraper"
        }
        self.sql = SQLRetriever()
        
        # Determine image directory from config
        try:
            config = mGetDBDConfig()
            self.img_dir = mGetFile(config['PERKS_IMG_DIR'])
            os.makedirs(self.img_dir, exist_ok=True)
        except Exception as e:
            mLogError(f"Could not load PERKS_IMG_DIR: {e}")
            self.img_dir = "assets/dbd/imgs/perks"
            os.makedirs(self.img_dir, exist_ok=True)

    def run(self):
        """Scrapes the wiki and updates the database with Survivor perks."""
        mLogInfo("Fetching Survivor Perks from the wiki...")
        response = requests.get(self.url, headers=self.headers)
        response.raise_for_status()

        html_content = response.json()["parse"]["text"]["*"]
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Use regex to find the Survivor Perks heading, ignoring the dynamic count number
        survivor_heading = soup.find(id=re.compile(r"Survivor_Perks_\(\d+\)"))
        if not survivor_heading:
            mLogError("Could not find the Survivor Perks section.")
            return

        survivor_table = survivor_heading.find_next("table", class_="wikitable")
        if not survivor_table:
            mLogError("Could not find survivor perks table.")
            return

        # Parse headers to dynamically find the Character column index
        header_row = survivor_table.find("tr")
        headers = [th.get_text(strip=True).lower() for th in header_row.find_all(["th", "td"])]
        char_col_idx = headers.index("character") if "character" in headers else 3

        rows = survivor_table.find_all("tr")[1:]  # skip header
        mLogInfo(f"Found {len(rows)} perks to process.")

        new_count = 0
        update_count = 0

        for row in rows:
            cols = row.find_all(["td", "th"])
            if len(cols) >= 4:
                # 1. Parse Image URL
                img_tag = cols[0].find("img")
                img_url = ""
                if img_tag:
                    img_url = img_tag.get("data-src") or img_tag.get("src")
                    if img_url and img_url.startswith("/"):
                        img_url = "https://deadbydaylight.wiki.gg" + img_url
                        
                    # Fetch high-resolution image instead of thumbnail
                    if "/thumb/" in img_url:
                        img_url = img_url.replace("/thumb/", "/")
                        img_url = img_url.rsplit("/", 1)[0] # remove the scaled /50px-... part

                # 2. Parse Text Data
                name = cols[1].get_text(separator=" ", strip=True)
                
                # The description often spans multiple languages or has extra data. We just want the readable text.
                desc_div = cols[2].find("div", class_="formattedPerkDesc")
                if desc_div:
                    description = desc_div.get_text(separator=" ", strip=True)
                else:
                    description = cols[2].get_text(separator=" ", strip=True)
                    
                # Clean up excess whitespace
                description = re.sub(r'\s+', ' ', description).strip()
                
                is_exhaustion = "Exhausted" in description

                # 3. Retrieve character ID from the Character column
                char_cell = cols[char_col_idx]
                char_link = char_cell.find("a")
                if char_link and char_link.get("title"):
                    character_name = char_link["title"]
                else:
                    character_name = char_cell.get_text(strip=True)

                owner_id = None
                if character_name.lower() not in ("all", ". all", ""):
                    owner_id = self.sql.mGetCharacterId(character_name)
                    if owner_id is None:
                        mLogInfo(f"Character '{character_name}' not found in database. Adding them.")
                        owner_id = self.sql.mInsertCharacter(character_name)
                else:
                    owner_id = self.sql.mGetCharacterId("ALL")

                # 4. Upsert Perk
                existing_perk = self.sql.mGetPerkByName(name)
                
                if existing_perk:
                    perk_id = existing_perk["id"]
                    uuid_str = existing_perk["uuid"]
                    if not uuid_str:
                        uuid_str = mGenerateProjectId()
                    
                    self.sql.mUpdatePerk(perk_id, uuid_str, owner_id, description, is_exhaustion)
                    update_count += 1
                else:
                    uuid_str = mGenerateProjectId()
                    self.sql.mInsertPerk(uuid_str, name, owner_id, description, is_exhaustion)
                    new_count += 1

                # 5. Download and save the image using generated UUID
                if img_url:
                    img_path = os.path.join(self.img_dir, f"{uuid_str}.png")
                    self.download_image(img_url, img_path)

        mLogInfo(f"Scrape complete! Inserted {new_count} new perks, Updated {update_count} existing perks.")

    def download_image(self, url: str, path: str):
        if not os.path.exists(path):
            try:
                img_data = requests.get(url, headers=self.headers).content
                with open(path, 'wb') as handler:
                    handler.write(img_data)
                mLogInfo(f"Downloaded image to {path}")
            except Exception as e:
                mLogError(f"Failed to download image {url}: {e}")
