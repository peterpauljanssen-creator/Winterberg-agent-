import requests
import json
import datetime
import os
from bs4 import BeautifulSoup

# --- JOUW GEGEVENS ---
TELEGRAM_TOKEN = "7816214855:AAFAr7TuoLZe2FRoqeDD_rAGovVvr_lKVmY"
TELEGRAM_CHAT_ID = "8546730577"

# --- INSTELLINGEN ---
LOCATIE = {"lat": 51.19, "lon": 8.53}
OPSLAG_BESTAND = "history.json"
EINDE_SEIZOEN = datetime.date(2026, 3, 31)

def get_next_saturday():
    """Berekent de datum van de eerstvolgende zaterdag"""
    vandaag = datetime.date.today()
    dagen_tot_zaterdag = (5 - vandaag.weekday()) % 7
    return vandaag + datetime.timedelta(days=dagen_tot_zaterdag)

def send_telegram(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        # disable_web_page_preview=True zorgt dat je chat niet volloopt met plaatjes van links,
        # maar als je dat wel wilt, haal die optie dan weg.
        data = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
        requests.post(url, data=data)
    except Exception as e:
        print(f"Fout bij Telegram: {e}")

def scrape_sneeuwhoogte():
    """Haalt actuele sneeuwhoogte op van Bergfex"""
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        url = "https://www.bergfex.nl/winterberg-skiliftkarussell/sneeuwhoogte/"
        r = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(r.content, 'html.parser')
        
        data = {"berg": "Onbekend", "dal": "Onbekend"}
        
        # Scrape logica voor Bergfex (zoekt naar de dikgedrukte centimeters)
        ranges = soup.find_all("div", class_="snow-depth-ranges__value")
        if len(ranges) >= 2:
            vals = [r.get_text(strip=True) for r in ranges]
            data["dal"] = vals[0]
            data["berg"] = vals[1]
            
        return data
    except Exception as e:
        print(f"Scraping fout: {e}")
        return {"berg": "?", "dal": "?"}

def get_weather():
    url = f"https://api.open-meteo.com/v1/forecast?latitude={LOCATIE['lat']}&longitude={LOCATIE['lon']}&daily=temperature_2m_max,temperature_2m_min,snowfall_sum,precipitation_probability_max&timezone=Europe%2FBerlin&forecast_days=16"
    return requests.get(url).json()

def main():
    print("Agent gestart...")
    vandaag = datetime.date.today()
    if vandaag > EINDE_SEIZOEN: return

    # 1. Bepaal doel datum
    target_date_obj = get_next_saturday()
    target_date_str = str(target_date_obj)
    
    # 2. Laad historie
    historie = []
    if os.path.exists(OPSLAG_BESTAND):
        with open(OPSLAG_BESTAND, 'r') as f:
            try: historie = json.load(f)
            except: historie = []

    # 3. Haal data op
    weer_data = get_weather()
    sneeuw_nu = scrape_sneeuwhoogte()

    if 'daily' not in weer_data: return
    dagen = weer_data['daily']['time']
    try: idx = dagen.index(target_date_str)
    except: return

    nieuwe_check = {
        "datum_check": str(vandaag),
        "doel_datum": target_date_str,
        "max": weer_data['daily']['temperature_2m_max'][idx],
        "min": weer_data['daily']['temperature_2m_min'][idx],
        "sneeuw_verwacht": weer_data['daily']['snowfall_sum'][idx],
        "neerslag_kans": weer_data['daily']['precipitation_probability_max'][idx],
        "sneeuw_nu_berg": sneeuw_nu['berg'],
        "sneeuw_nu_dal": sneeuw_nu['dal']
    }

    # 4. Trend Analyse
    trend_tekst = ""
    if historie:
        vorige = historie[-1]
        # Probeer sneeuwhoogte verschil te berekenen
        try:
            nu_b = int(nieuwe_check['sneeuw_nu_berg'].replace('cm','').strip())
            oud_b = int(vorige['sneeuw_nu_berg'].replace('cm','').strip())
            diff = nu_b - oud_b
            if diff > 0: trend_tekst += f"❄️ Sneeuwval Berg: +{diff} cm!\n"
            elif diff < 0: trend_tekst += f"🔥 Sneeuwsmelt Berg: {diff} cm\n"
        except: pass

    # 5. Bericht (MET NIEUWE LINK)
    bericht = (f"🏔️ **Winterberg Update**\n"
               f"📅 Focus op zaterdag: {target_date_str}\n\n"
               f"📏 **Actuele Sneeuwhoogte:**\n"
               f"🏔️ Berg: {nieuwe_check['sneeuw_nu_berg']}\n"
               f"🏘️ Dal: {nieuwe_check['sneeuw_nu_dal']}\n"
               f"{trend_tekst}\n"
               f"🔮 **Voorspelling Zaterdag:**\n"
               f"🌡️ {nieuwe_check['min']}°C tot {nieuwe_check['max']}°C\n"
               f"❄️ Verwacht: {nieuwe_check['sneeuw_verwacht']} cm\n\n"
               f"🔗 [Bergfex Sneeuwhoogte](https://www.bergfex.nl/winterberg-skiliftkarussell/sneeuwhoogte/)\n"
               f"🎥 [Wettercams Winterberg](https://www.skiliftkarussell.de/nl/stroom/360-live-mediacam/)")
    
    send_telegram(bericht)

    # 6. Opslaan
    historie.append(nieuwe_check)
    if len(historie) > 50: historie = historie[-50:]
    with open(OPSLAG_BESTAND, 'w') as f:
        json.dump(historie, f)

if __name__ == "__main__":
    main()
    
