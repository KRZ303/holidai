import csv
import json
import os
import sys
import time
import subprocess
import select
import socket
from urllib.parse import urlparse

# SCRIPT LOCATION & PATH SETUP
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_ENCODING = "utf-8-sig"
PYTHON_EVAL_TIMEOUT_SECONDS = 60
CHROME_BINARY = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
CHROME_PROFILE_DIR = os.path.join(SCRIPT_DIR, "chrome-profile")

# Default input CSV path
DEFAULT_CSV = "/Users/krz/Dev/holidai/research/booking_matrix_turcja_kreta.csv"

# Accept CSV path as command line argument
if len(sys.argv) > 1:
    CSV_PATH = os.path.abspath(sys.argv[1])
else:
    CSV_PATH = DEFAULT_CSV

if not os.path.exists(CSV_PATH):
    print(f"Error: Input CSV file not found at: {CSV_PATH}")
    print(f"Usage: python3 {sys.argv[0]} [path_to_matrix.csv]")
    sys.exit(1)

# Generate dynamic output paths inside the 'scrape' directory
csv_base = os.path.splitext(os.path.basename(CSV_PATH))[0]

OUTPUT_CSV_PATH = os.path.join(SCRIPT_DIR, f"{csv_base}_VERIFIED.csv")
CACHE_PATH = os.path.join(SCRIPT_DIR, f"{csv_base}_cache.json")
MD_DIR = os.path.join(SCRIPT_DIR, f"{csv_base}_MD")
DISCREPANCIES_PATH = os.path.join(SCRIPT_DIR, f"{csv_base}_discrepancies.md")

JS_COOKIE_ACCEPT = """
(() => {
  const acceptBtn = Array.from(document.querySelectorAll('button')).find(btn => 
    btn.innerText.trim() === 'Accept' || 
    btn.innerText.trim() === 'Zaakceptuj' || 
    btn.innerText.trim() === 'Akceptuję' ||
    btn.innerText.trim() === 'Akceptuj'
  );
  if (acceptBtn) {
    acceptBtn.click();
    return 'cookie_clicked';
  }
  return 'no_cookie_banner';
})()
"""

JS_VERIFY = """
async () => {
  // 1. Expand facilities
  const trigger = document.getElementById('facilities-tab-trigger');
  if (trigger) {
    trigger.click();
    await new Promise(resolve => setTimeout(resolve, 800));
  }

  // 2. Scroll to load comments/reviews and other dynamic elements
  window.scrollTo(0, document.body.scrollHeight / 2);
  await new Promise(resolve => setTimeout(resolve, 500));
  window.scrollTo(0, document.body.scrollHeight);
  await new Promise(resolve => setTimeout(resolve, 500));

  const data = {};
  
  // Title
  data.title = document.querySelector('h2.pp-header__title')?.innerText.trim() || '';
  if (!data.title) {
    data.title = document.querySelector('[data-testid="PropertyHeaderName"]')?.innerText.trim() || '';
  }

  // Address
  const addressEl = document.querySelector('#map_trigger_header_pin') || document.querySelector('.hp_address_subtitle') || document.querySelector('[data-testid="button-show-on-map"]');
  data.address = addressEl ? addressEl.innerText.trim().replace(/\\n/g, ' ') : '';

  // Coordinates
  const mapLink = document.querySelector('#map_trigger_header_pin') || document.querySelector('[data-atlas-latlng]');
  data.mapCoords = mapLink ? (mapLink.getAttribute('data-atlas-latlng') || mapLink.getAttribute('data-bbox') || '') : '';

  // Photos (visible images, no gallery open)
  const photoEls = Array.from(document.querySelectorAll('.bh-photo-grid-item img, .hp-gallery-grid img, [data-testid="image-grid-cell"] img, .hp-gallery-slides img, img.photos_grid_photo_img'));
  data.photos = [...new Set(photoEls.map(img => img.src || img.getAttribute('data-lazy') || img.getAttribute('data-src') || '').filter(Boolean))].slice(0, 12);

  // Description
  const descEl = document.querySelector('#property_description_content') || document.querySelector('.hp-description');
  data.description = descEl ? descEl.innerText.trim() : '';

  // Rating & Reviews
  const scoreBlock = document.querySelector('[data-testid="review-score-component"]');
  data.rating = null;
  data.reviewsCount = 0;
  if (scoreBlock) {
    const text = scoreBlock.innerText || '';
    const ratingMatch = text.match(/(\\d[\\.,]\\d)/);
    if (ratingMatch) {
      data.rating = parseFloat(ratingMatch[1].replace(',', '.'));
    }
    const reviewsMatch = text.match(/(\\d+)\\s*(opini|review|opinie|guest)/i);
    if (reviewsMatch) {
      data.reviewsCount = parseInt(reviewsMatch[1], 10);
    }
  }

  // Popular Amenities
  const amHeader = Array.from(document.querySelectorAll('h3')).find(h => h.innerText.includes('Most popular amenities') || h.innerText.includes('Najpopularniejsze udogodnienia'));
  data.popularAmenities = [];
  if (amHeader && amHeader.nextElementSibling) {
    data.popularAmenities = Array.from(amHeader.nextElementSibling.querySelectorAll('span')).map(el => el.innerText.trim()).filter(Boolean);
  }

  // All facilities
  const facEl = document.querySelector('#hp_facilities_box') || document.querySelector('[data-testid="property-section-facilities"]') || document.querySelector('.hp-facilities-box') || document.querySelector('.facilitiesChecklist');
  data.allFacilities = facEl ? facEl.innerText.trim() : '';
  const facItems = facEl ? Array.from(facEl.querySelectorAll('li, [class*="facility-item"], [data-testid="facility-item"]')).map(el => el.innerText.trim()).filter(Boolean) : [];
  data.facilitiesList = [...new Set(facItems)];

  // Area Info (Otoczenie obiektu)
  const areaSec = Array.from(document.querySelectorAll('.hotelchars .page-section, #basiclayout .page-section, [data-testid="property-section-surroundings"]')).find(sec => sec.innerText.includes('Area info') || sec.innerText.includes('Okolica') || sec.innerText.includes('W pobliżu') || sec.innerText.includes('Co jest w pobliżu'));
  if (areaSec) {
    data.areaInfoText = areaSec.innerText.trim();
  } else {
    const neighborhoodEl = document.querySelector('.hp-neighborhood, [data-testid="property-section-surroundings"]');
    data.areaInfoText = neighborhoodEl ? neighborhoodEl.innerText.trim() : 'Brak szczegółowych informacji o otoczeniu.';
  }

  // House Rules
  const rulesSec = document.querySelector('.k2-hp--facilities_and_policies') || Array.from(document.querySelectorAll('.hotelchars .page-section, #basiclayout .page-section, [data-testid="property-section-policies"]')).find(sec => sec.innerText.includes('House rules') || sec.innerText.includes('Zasady obiektu') || sec.innerText.includes('Zasady działalności obiektu'));
  data.houseRules = rulesSec ? rulesSec.innerText.trim() : 'Brak sekcji z zasadami pobytu.';

  // Important Info
  const impInfoEl = document.querySelector('#important_info_wrapper') || document.querySelector('.hp-important_info') || document.querySelector('[data-testid="important_info"]') || document.querySelector('#policies_linkbox_wrapper');
  data.importantInfo = impInfoEl ? impInfoEl.innerText.trim() : 'Brak sekcji Ważne Informacje.';

  // Room Table to Markdown conversion
  const table = document.querySelector('.hprt-table') || document.querySelector('#hp_rt_table');
  let roomTableMd = 'Tabela pokoi nie została znaleziona.';
  if (table) {
    const headers = Array.from(table.querySelectorAll('thead th')).map(th => th.innerText.trim().replace(/\\n/g, ' '));
    const rows = [];
    table.querySelectorAll('tbody tr').forEach(tr => {
      if (tr.classList.contains('hprt-table-cheapest-block') || tr.style.display === 'none') return;
      const cols = Array.from(tr.querySelectorAll('td, th')).map(td => {
        return td.innerText.trim().replace(/\\n/g, ' <br> ').replace(/\\|/g, '\\\\|');
      });
      if (cols.length > 0) {
        rows.push('| ' + cols.join(' | ') + ' |');
      }
    });
    if (rows.length > 0) {
      const headerLine = '| ' + headers.join(' | ') + ' |';
      const sepLine = '| ' + headers.map(() => '---').join(' | ') + ' |';
      roomTableMd = [headerLine, sepLine, ...rows].join('\\n');
    }
  }
  data.roomTableMd = roomTableMd;

  // Guest Reviews comments
  const reviews = [];
  document.querySelectorAll('.ee4cb4021c, .featuredreviewcard, .reviewFloater, .fe4dfbc0c7 .c3bdfd4ac2, .review_item, [data-testid="review-card"]').forEach(card => {
    const name = card.querySelector('.a787c7cca4, .featuredreviewcard-avatar-name, .reviewer_name, [data-testid="review-card-reviewer-name"]')?.innerText.trim() || '';
    const text = card.querySelector('.e01adb21c0, .featuredreviewcard-text, .d14152e7c3, .review_item_header_content, [data-testid="review-card-text"]')?.innerText.trim() || '';
    if (name || text) {
      reviews.push({ name, text });
    }
  });
  data.reviewsList = reviews.slice(0, 10);

  // General text checks for attributes
  const lowerHtml = document.body.innerText.toLowerCase();
  const roomTexts = Array.from(document.querySelectorAll('a[data-testid="rt-name-link"], .hprt-roomtype-icon-link, [data-testid="room-title"]')).map(el => {
    const parent = el.closest('tr') || el.closest('[data-testid="room-row"]') || el.parentElement;
    return parent ? parent.innerText.toLowerCase() : '';
  }).join(' ');

  const facTextLower = data.allFacilities.toLowerCase();
  const combinedText = (lowerHtml + ' ' + roomTexts + ' ' + facTextLower);

  const pralka_in_facilities = facTextLower.includes('pralka') || facTextLower.includes('pralki') || facTextLower.includes('pralkę') || facTextLower.includes('washing machine') || roomTexts.includes('pralka') || roomTexts.includes('pralki') || roomTexts.includes('pralkę') || roomTexts.includes('washing machine');
  const pralka_anywhere = lowerHtml.includes('pralka') || lowerHtml.includes('pralki') || lowerHtml.includes('pralkę') || lowerHtml.includes('washing machine');

  if (pralka_in_facilities) {
    data.pralka_potwierdzona = true;
    data.pralka_tylko_opinia = false;
  } else if (pralka_anywhere) {
    data.pralka_potwierdzona = false;
    data.pralka_tylko_opinia = true;
  } else {
    data.pralka_potwierdzona = false;
    data.pralka_tylko_opinia = false;
  }

  data.hasLaundryService = combinedText.includes('pralnia') || combinedText.includes('laundry') || combinedText.includes('dry cleaning') || combinedText.includes('prasowanie') || combinedText.includes('ironing') || combinedText.includes('pralnia chemiczna');
  data.hasKitchen = combinedText.includes('kuchnia') || combinedText.includes('kitchen') || combinedText.includes('kitchenette') || combinedText.includes('lodówka') || combinedText.includes('refrigerator') || combinedText.includes('płyta kuchenna') || combinedText.includes('stovetop') || combinedText.includes('aneks kuchenny');
  data.hasPrivateBathroom = combinedText.includes('prywatna łazienka') || combinedText.includes('private bathroom') || combinedText.includes('łazienka w pokoju') || combinedText.includes('en suite bathroom') || combinedText.includes('łazienka');
  data.hasBeachfront = combinedText.includes('przy samej plaży') || combinedText.includes('beachfront') || combinedText.includes('lokalizacja przy samej plaży') || combinedText.includes('prywatna plaża') || combinedText.includes('private beach') || combinedText.includes('plaża przy obiekcie');
  data.hasSeaView = combinedText.includes('widok na morze') || combinedText.includes('sea view') || combinedText.includes('ocean view') || combinedText.includes('widokiem na morze');
  data.hasParking = combinedText.includes('parking') || combinedText.includes('garaż') || combinedText.includes('car park');

  // Find price
  const priceElements = Array.from(document.querySelectorAll('.bui-price-display__value, .prco-valign-middle-helper, [data-testid="price-and-discount-next-to-each-other"]'))
    .map(el => {
      const text = el.innerText || '';
      const clean = text.replace(/[^\\d]/g, '');
      return clean ? parseInt(clean, 10) : null;
    })
    .filter(Boolean);
  data.minPrice = priceElements.length ? Math.min(...priceElements) : null;

  return JSON.stringify(data);
}
"""

def is_port_open(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1.0)
        try:
            s.connect(('127.0.0.1', port))
            return True
        except OSError:
            return False

def read_csv_rows(csv_path):
    with open(csv_path, "r", encoding=CSV_ENCODING, newline="") as f:
        reader = csv.DictReader(f)
        return reader.fieldnames, list(reader)

def get_country_name(row):
    return row.get("kraj") or row.get("\ufeffkraj") or row.get("Destynacja") or "Destynacja"

def build_property_key(row):
    link = row.get("link")
    if not link:
        return None
    parsed = urlparse(link)
    base_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
    hotel_name = (row.get("nazwa") or "").strip()
    return (base_url, hotel_name)

def group_rows_by_property(rows):
    unique_hotels = {}
    for idx, row in enumerate(rows, start=2):
        key = build_property_key(row)
        if key is None:
            continue
        unique_hotels.setdefault(key, []).append((idx, row))
    return unique_hotels

def confirm_booking_tab_ready():
    print("\n======================================================================")
    print("Confirm Google Chrome is logged in to Booking.com and exactly one")
    print("Booking.com tab is open in the debug session.")
    print("Type OK to continue. Any other input exits before navigation.")
    print("======================================================================")
    confirmation = input("> ").strip()
    if confirmation != "OK":
        print("Did not receive OK. Exiting before navigation.")
        return False
    return True

def ensure_browser():
    if is_port_open(9222):
        print("Found active Chrome debugger on port 9222.")
        return True
        
    print("No active Chrome debugger found on port 9222. Attempting to launch Google Chrome...")
    if not os.path.exists(CHROME_BINARY):
        print("Error: Google Chrome was not found at /Applications/Google Chrome.app/Contents/MacOS/Google Chrome.")
        print("Install stable Google Chrome or launch it manually with:")
        print(f"  {CHROME_BINARY} --remote-debugging-port=9222 --user-data-dir={CHROME_PROFILE_DIR} https://www.booking.com")
        return False
        
    os.makedirs(CHROME_PROFILE_DIR, exist_ok=True)
    
    cmd = [
        CHROME_BINARY,
        "--remote-debugging-port=9222",
        f"--user-data-dir={CHROME_PROFILE_DIR}",
        "https://www.booking.com"
    ]
    
    print("Launching Google Chrome...")
    subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    # Wait for port to open
    for _ in range(20):
        time.sleep(0.5)
        if is_port_open(9222):
            print("Chrome started and listening on port 9222.")
            break
    else:
        print("Error: Timed out waiting for Chrome to listen on port 9222.")
        return False
    return True

def run_agent_browser_open(url):
    try:
        helper_path = os.path.join(os.path.dirname(SCRIPT_DIR), "chrome-scrape-control", "cdp_helper.js")
        proc = subprocess.run(["node", helper_path, "navigate", url], capture_output=True, text=True, timeout=40)
        if proc.returncode == 0:
            return True, None
        else:
            return False, proc.stderr.strip()
    except Exception as e:
        return False, str(e)

def run_agent_browser_eval(script, timeout=PYTHON_EVAL_TIMEOUT_SECONDS):
    try:
        helper_path = os.path.join(os.path.dirname(SCRIPT_DIR), "chrome-scrape-control", "cdp_helper.js")
        proc = subprocess.Popen(["node", helper_path, "eval"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            stdout, stderr = proc.communicate(input=script, timeout=timeout)
        except subprocess.TimeoutExpired:
            proc.kill()
            stdout, stderr = proc.communicate()
            timeout_message = f"Timed out after {timeout} seconds while evaluating browser script."
            if stderr.strip():
                timeout_message = f"{timeout_message} {stderr.strip()}"
            return None, timeout_message
        if proc.returncode == 0:
            return stdout.strip(), None
        else:
            return None, stderr.strip()
    except Exception as e:
        return None, str(e)

def load_cache():
    if os.path.exists(CACHE_PATH):
        try:
            with open(CACHE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_cache(cache):
    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)

def prompt_user_stuck(message):
    print(f"\n[ALERT] {message}")
    print("Press ENTER in terminal to retry immediately. If no answer is received in 20 seconds, we will proceed with TBD.")
    rlist, _, _ = select.select([sys.stdin], [], [], 20)
    if rlist:
        sys.stdin.readline()
        return "retry"
    else:
        print("Timeout! Skipping and setting price to TBD.")
        return "tbd"

def main():
    if not ensure_browser():
        print("Failed to ensure browser is running. Exiting.")
        sys.exit(1)
    if not confirm_booking_tab_ready():
        sys.exit(0)
        
    os.makedirs(MD_DIR, exist_ok=True)
    cache = load_cache()
    
    print(f"Reading CSV file {CSV_PATH}...")
    fieldnames, rows = read_csv_rows(CSV_PATH)
            
    print(f"Loaded {len(rows)} rows from CSV.")
    
    unique_hotels = group_rows_by_property(rows)
    print(f"Mapped {len(unique_hotels)} unique properties from CSV.")
    
    # Calculate progress
    # Let's count how many unique hotels are already completely cached in cache
    cached_count = 0
    for _, occurrence_list in unique_hotels.items():
        all_cached = True
        for row_idx, r in occurrence_list:
            url = r.get('link')
            if f"{url}_v2" not in cache:
                all_cached = False
                break
        if all_cached:
            cached_count += 1
            
    print(f"Progress: {cached_count}/{len(unique_hotels)} unique hotels already verified in cache.")
    
    # Process unique hotels
    for hotel_idx, ((base_url, hotel_name), occurrence_list) in enumerate(unique_hotels.items(), 1):
        first_row_idx, first_row = occurrence_list[0]
        country = get_country_name(first_row)
        
        # Check if all links for this hotel are already cached
        all_cached = True
        for _, r in occurrence_list:
            if f"{r.get('link')}_v2" not in cache:
                all_cached = False
                break
        if all_cached:
            # Reconstruct stay prices from cache to ensure we can write to MD and CSV
            stay_prices = {}
            scraped_data_obj = None
            for _, r in occurrence_list:
                url = r.get('link')
                days = r.get('dni')
                scraped_data_obj = cache[f"{url}_v2"]
                stay_prices[days] = scraped_data_obj.get('minPrice')
        else:
            print(f"\n--- [{hotel_idx}/{len(unique_hotels)}] Hotel: {hotel_name} ({country}) ---")
            stay_prices = {}
            scraped_data_obj = None
            skip_remaining = False
            tbd_marked = False
            
            for row_idx, r in occurrence_list:
                url = r.get('link')
                days = r.get('dni')
                
                # Check cache first
                cache_key = f"{url}_v2"
                if cache_key in cache:
                    print(f"  Loaded {days} days from cache: {cache[cache_key].get('minPrice')} PLN")
                    scraped_data_obj = cache[cache_key]
                    stay_prices[days] = scraped_data_obj.get('minPrice')
                    continue
                    
                print(f"  Navigating to {days} days URL...")
                
                # Navigate
                success, err = run_agent_browser_open(url)
                if not success:
                    action = prompt_user_stuck(f"Failed to open page for {hotel_name} ({days} days). Error: {err}")
                    if action == "retry":
                        success, err = run_agent_browser_open(url)
                    if not success:
                        print("  Failed again, marking prices as TBD.")
                        tbd_marked = True
                        skip_remaining = True
                        break
                        
                time.sleep(5)
                
                # Accept cookies
                run_agent_browser_eval(JS_COOKIE_ACCEPT)
                
                # Verify and extract
                res_str, err = run_agent_browser_eval(JS_VERIFY)
                if err or not res_str:
                    action = prompt_user_stuck(f"Failed to scrape page for {hotel_name} ({days} days). Error: {err}")
                    if action == "retry":
                        res_str, err = run_agent_browser_eval(JS_VERIFY)
                    if not res_str:
                        print("  Failed again, marking prices as TBD.")
                        tbd_marked = True
                        skip_remaining = True
                        break
                        
                try:
                    if res_str.startswith('"') and res_str.endswith('"'):
                        res_str = json.loads(res_str)
                    data = json.loads(res_str)
                    
                    if not data.get('title'):
                        action = prompt_user_stuck(f"Empty title / CAPTCHA on {hotel_name} ({days} days).")
                        if action == "retry":
                            res_str, err = run_agent_browser_eval(JS_VERIFY)
                            if res_str.startswith('"') and res_str.endswith('"'):
                                res_str = json.loads(res_str)
                            data = json.loads(res_str)
                        if not data.get('title'):
                            print("  Skipping with TBD.")
                            tbd_marked = True
                            skip_remaining = True
                            break
                            
                    scraped_data_obj = data
                    stay_prices[days] = data.get('minPrice')
                    print(f"    Price found: {data.get('minPrice')} PLN")
                    
                    # Cache it
                    cache[cache_key] = data
                    save_cache(cache)
                    
                except Exception as e:
                    print(f"  Error parsing response data: {e}")
                    tbd_marked = True
                    skip_remaining = True
                    break
                    
                time.sleep(3)
                
            if skip_remaining:
                for _, r in occurrence_list:
                    days = r.get('dni')
                    stay_prices[days] = "TBD" if tbd_marked else "-1"
                if not scraped_data_obj:
                    scraped_data_obj = {
                        "title": hotel_name,
                        "address": first_row.get('address', ''),
                        "mapCoords": "",
                        "photos": [],
                        "description": "Brak danych z powodu błędu lub CAPTCHA.",
                        "rating": None,
                        "reviewsCount": 0,
                        "popularAmenities": [],
                        "facilitiesList": [],
                        "areaInfoText": "Brak danych.",
                        "roomTableMd": "Brak danych.",
                        "reviewsList": [],
                        "houseRules": "Brak danych.",
                        "importantInfo": "Brak danych.",
                        "pralka_potwierdzona": False,
                        "pralka_tylko_opinia": False,
                        "hasLaundryService": False,
                        "hasKitchen": False,
                        "hasPrivateBathroom": False,
                        "hasBeachfront": False,
                        "hasSeaView": False,
                        "hasParking": False
                    }
                
        # Generate Markdown File for this hotel exactly matching sections A-F
        clean_hotel_name = "".join(c for c in hotel_name if c.isalnum() or c in " -_").strip()
        md_filename = f"{country}-{clean_hotel_name}.md"
        md_path = os.path.join(MD_DIR, md_filename)
        
        print(f"  Writing hotel details to: {md_filename}...")
        
        # Build photos markdown list
        photos_list_md = ""
        for photo_url in scraped_data_obj.get('photos', []):
            photos_list_md += f"- {photo_url}\n"
        if not photos_list_md:
            photos_list_md = "Brak widocznych zdjęć z siatki.\n"
            
        # Build reviews list
        reviews_list_md = ""
        for rev_item in scraped_data_obj.get('reviewsList', []):
            reviews_list_md += f"**{rev_item.get('name', 'Gość')}**:\n> {rev_item.get('text', '')}\n\n"
        if not reviews_list_md:
            reviews_list_md = "Brak widocznych opinii.\n"
            
        # Build summary points
        has_pralka = scraped_data_obj.get('pralka_potwierdzona', False)
        has_opinia = scraped_data_obj.get('pralka_tylko_opinia', False)
        has_usluga = scraped_data_obj.get('hasLaundryService', False)
        
        summary_pralka = "Brak pralki i usług prania."
        if has_pralka and has_usluga:
            summary_pralka = "Tak, pralka dostępna w pokoju/apartamencie oraz dostępna usługa prania."
        elif has_pralka:
            summary_pralka = "Tak, pralka dostępna w pokoju/apartamencie."
        elif has_opinia and has_usluga:
            summary_pralka = "Brak oficjalnej pralki w pokoju, ale goście wspomnieli o pralce w opiniach, a obiekt świadczy usługę prania."
        elif has_usluga:
            summary_pralka = "Brak pralki w pokoju. Obiekt oferuje tylko usługę prania (laundry service - dodatkowo płatna)."
        elif has_opinia:
            summary_pralka = "Obiekt nie deklaruje pralki w udogodnieniach, ale goście w opiniach wspominają, że pralka jest dostępna."
            
        summary_beach = "Brak danych."
        if first_row.get('plaza_booking'):
            summary_beach = first_row.get('plaza_booking')
            if scraped_data_obj.get('hasBeachfront'):
                summary_beach += " (Lokalizacja bezpośrednio przy plaży / beachfront)"
                
        summary_bathroom = "Tak, pokoje posiadają prywatną łazienkę." if scraped_data_obj.get('hasPrivateBathroom') else "Niepotwierdzona w udogodnieniach."
        
        rating = scraped_data_obj.get('rating')
        if rating is not None:
            if rating >= 9.0:
                summary_ratio = "Bardzo dobry stosunek ceny do jakości (znakomite opinie gości)."
            elif rating >= 8.0:
                summary_ratio = "Dobry / zadowalający stosunek ceny do jakości."
            else:
                summary_ratio = "Przeciętny, ocena obiektu jest poniżej 8.0."
        else:
            summary_ratio = "Trudno ocenić (brak ocen na Booking.com)."
            
        md_content = f"""# {country} - {hotel_name}

## A) Sekcja Nagłówkowa
- **Nazwa obiektu:** {scraped_data_obj.get('title', hotel_name)}
- **Adres:** {scraped_data_obj.get('address', 'Brak adresu')}
- **Współrzędne:** {scraped_data_obj.get('mapCoords', 'Brak współrzędnych')}
- **Widoczne zdjęcia:**
{photos_list_md}
- **Opis obiektu:**
{scraped_data_obj.get('description', 'Brak opisu.')}

## B) Dostępność i Tabela Pokoi
- **Ceny za okresy pobytu:**
  - **8 dni (16.09 - 24.09):** {stay_prices.get('8', '-1')} PLN
  - **11 dni (16.09 - 27.09):** {stay_prices.get('11', '-1')} PLN
  - **14 dni (16.09 - 30.09):** {stay_prices.get('14', '-1')} PLN

- **Dokładna tabela pokoi:**
{scraped_data_obj.get('roomTableMd', 'Brak tabeli pokoi.')}

## C) Opinie Gości
- **Ocena ogólna:** {scraped_data_obj.get('rating', 'Brak')} / 10
- **Liczba opinii:** {scraped_data_obj.get('reviewsCount', 0)}

- **Lista komentarzy:**
{reviews_list_md}

## D) Otoczenie obiektu
{scraped_data_obj.get('areaInfoText', 'Brak informacji o otoczeniu.')}

## E) Udogodnienia w obiekcie
- **Weryfikacja pralki:** {summary_pralka}
- **Wszystkie udogodnienia:**
{", ".join(scraped_data_obj.get('facilitiesList', [])) if scraped_data_obj.get('facilitiesList') else 'Brak szczegółowych udogodnień.'}

## F) Zasady pobytu i Ważne Informacje
- **Zasady pobytu (House Rules):**
```
{scraped_data_obj.get('houseRules', 'Brak zasad.')}
```
- **Ważne Informacje (Important Info):**
```
{scraped_data_obj.get('importantInfo', 'Brak ważnych informacji.')}
```

## Podsumowanie i ocena autorska:
- **Odległość od plaży:** {summary_beach}
- **Prywatna łazienka:** {summary_bathroom}
- **Stosunek ceny do jakości:** {summary_ratio}
- **Ogólne podsumowanie:** Obiekt w kategorii {first_row.get('wariant')}. Szczegółowe udogodnienia zostały zweryfikowane automatycznie.
"""
        with open(md_path, "w", encoding="utf-8") as f_md:
            f_md.write(md_content)
            
        # Update the CSV rows in memory
        for row_idx, r in occurrence_list:
            days = r.get('dni')
            price_val = stay_prices.get(days, '-1')
            if price_val == "TBD":
                r['cena_pln'] = "TBD"
            elif price_val == "-1" or price_val is None:
                r['cena_pln'] = "-1"
            else:
                r['cena_pln'] = f"{price_val}.00"
                
            r['ocena_booking'] = str(scraped_data_obj.get('rating', '')) if scraped_data_obj.get('rating') else ''
            r['opinie_booking'] = str(scraped_data_obj.get('reviewsCount', '0'))
            r['pralka_potwierdzona'] = str(scraped_data_obj.get('pralka_potwierdzona', False))
            r['pralka_tylko_opinia'] = str(scraped_data_obj.get('pralka_tylko_opinia', False))
            r['usluga_prania'] = str(scraped_data_obj.get('hasLaundryService', False))
            r['kuchnia'] = str(scraped_data_obj.get('hasKitchen', False))
            r['prywatna_lazienka'] = str(scraped_data_obj.get('hasPrivateBathroom', False))
            r['beachfront'] = str(scraped_data_obj.get('hasBeachfront', False))
            r['sea_view'] = str(scraped_data_obj.get('hasSeaView', False))
            r['parking'] = str(scraped_data_obj.get('hasParking', False))
            
            p_potw = scraped_data_obj.get('pralka_potwierdzona', False)
            p_opinia = scraped_data_obj.get('pralka_tylko_opinia', False)
            p_usl = scraped_data_obj.get('hasLaundryService', False)
            if p_potw and p_usl:
                r['status_prania'] = "Pralnia i pralka potwierdzone w udogodnieniach obiektu"
            elif p_potw:
                r['status_prania'] = "Pralka w pokoju/obiektu potwierdzona; usługa prania niepotwierdzona"
            elif p_opinia and p_usl:
                r['status_prania'] = "Pralnia/usługa prania potwierdzona; pralka w opiniach"
            elif p_usl:
                r['status_prania'] = "Pralnia/usługa prania potwierdzona w udogodnieniach obiektu"
            elif p_opinia:
                r['status_prania'] = "Pralka w pokoju/obiektu niepotwierdzona; pralka tylko w opiniach"
            else:
                r['status_prania'] = "Brak pralki/pralni w udogodnieniach obiektu"
                
    # Write the new CSV file
    print(f"\nWriting verified CSV to: {OUTPUT_CSV_PATH}...")
    with open(OUTPUT_CSV_PATH, "w", encoding="utf-8", newline="") as f_out:
        writer = csv.DictWriter(f_out, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
        
    # Generate discrepancy report
    print(f"Generating discrepancies report to: {DISCREPANCIES_PATH}...")
    discrepancies = []
    
    _, orig_rows = read_csv_rows(CSV_PATH)
        
    for i, (orig, updated) in enumerate(zip(orig_rows, rows), start=2):
        name = orig.get('nazwa')
        days = orig.get('dni')
        diffs = []
        for field in fieldnames:
            if orig[field] != updated[field]:
                diffs.append(f"{field}: '{orig[field]}' -> '{updated[field]}'")
        if diffs:
            discrepancies.append(f"Row {i} ({name}, {days} dni): " + ", ".join(diffs))
            
    with open(DISCREPANCIES_PATH, "w", encoding="utf-8") as f_disc:
        f_disc.write("# Raport Rozbieżności w Weryfikacji Booking Matrix\n\n")
        f_disc.write(f"Łączna liczba wierszy ze zmianami: {len(discrepancies)}\n\n")
        for diff in discrepancies:
            f_disc.write(f"- {diff}\n")
            
    print("Done!")

if __name__ == "__main__":
    main()
