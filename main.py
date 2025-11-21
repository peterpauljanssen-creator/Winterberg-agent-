import requests
import json
import datetime
import os

# --- JOUW GEGEVENS (Vul deze in!) ---
TELEGRAM_TOKEN = "7816214855:AAFAr7TuoLZe2FRoqeDD_rAGovVvr_lKVmY" 
TELEGRAM_CHAT_ID = "8546730577"

# --- INSTELLINGEN ---
DOEL_DATUM = "2025-12-07" # Let op: Jaartal klopt nu
LOCATIE = {"lat": 51.19, "lon": 8.53} # Winterberg
OPSLAG_BESTAND = "history.json"

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"})

def get_weather():url = f"https://api.open-meteo.com/v1/forecast?latitude={LOCATIE['lat']}&longitude={LOCATIE['lon']}&daily=temperature_2m_max,temperature_2m_min,snowfall_sum,precipitation_probability_max&timezone=Europe%2FBerlin&forecast_days=16"
    url = f"https://api.open-meteo.com/v1/"
    return requests.get(url).json()

def main():
    print("Agent gestart...")
    
    # 1. Historie laden
    historie = []
    if os.path.exists(OPSLAG_BESTAND):
        with open(OPSLAG_BESTAND, 'r') as f:
            try: historie = json.load(f)
            except: historie = []

    # 2. Nieuwe data ophalen
    data = get_weather()
    dagen = data['daily']['time']
    
    try:
        idx = dagen.index(DOEL_DATUM)
    except ValueError:
        send_telegram(f"⚠️ Datum {DOEL_DATUM} nog niet in voorspelling (max 16 dagen vooruit).")
        return

    vandaag = {
        "datum_check": str(datetime.date.today()),
        "max": data['daily']['temperature_2m_max'][idx],
        "min": data['daily']['temperature_2m_min'][idx],
        "sneeuw": data['daily']['snowfall_sum'][idx],
        "neerslag": data['daily']['precipitation_probability_max'][idx]
    }

    # 3. Vergelijken
    trend_msg = ""
    # Pak de laatste 3 checks, nieuwste eerst
    vorige_checks = sorted(historie, key=lambda x: x['datum_check'], reverse=True)[:3]
    
    if vorige_checks:
        trend_msg = "\n📉 *Trend t.o.v. vorige dagen:*\n"
        for oud in vorige_checks:
            diff_temp = vandaag['max'] - oud['max']
            diff_snow = vandaag['sneeuw'] - oud['sneeuw']
            
            pijl_t = "🔺" if diff_temp > 0 else "🔻"
            pijl_s = "meer ❄️" if diff_snow > 0 else "minder ❄️"
            if diff_snow == 0: pijl_s = "stabiel"
            
            trend_msg += f"- Check {oud['datum_check'][5:]}: {abs(round(diff_temp,1))}°C {pijl_t} & {pijl_s}\n"

    # 4. Bericht sturen
    bericht = (f"🏔️ **Winterberg Update**\n"
               f"📅 Voor: {DOEL_DATUM}\n\n"
               f"🌡️ Max: {vandaag['max']}°C (Min: {vandaag['min']}°C)\n"
               f"❄️ Sneeuw: {vandaag['sneeuw']} cm\n"
               f"☔ Neerslagkans: {vandaag['neerslag']}%\n"
               f"{trend_msg}\n"
               f"🔗 [Live Pistes](https://www.skiliftkarussell.de/nl/actueel/liften-en-pistes/)")
    
    send_telegram(bericht)

    # 5. Opslaan voor morgen
    historie.append(vandaag)
    with open(OPSLAG_BESTAND, 'w') as f:
        json.dump(historie, f)

if __name__ == "__main__":
    main()
