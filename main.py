import requests
import json
import datetime
import os

# --- JOUW GEGEVENS ---
TELEGRAM_TOKEN = "7816214855:AAFAr7TuoLZe2FRoqeDD_rAGovVvr_lKVmY"
TELEGRAM_CHAT_ID = "8546730577"

# --- INSTELLINGEN ---
LOCATIE = {"lat": 51.19, "lon": 8.53} # Winterberg
OPSLAG_BESTAND = "history.json"
EINDE_SEIZOEN = datetime.date(2026, 3, 31)

def get_next_saturday():
    """Berekent de datum van de eerstvolgende zaterdag (of vandaag als het zaterdag is)"""
    vandaag = datetime.date.today()
    dagen_tot_zaterdag = (5 - vandaag.weekday()) % 7
    return vandaag + datetime.timedelta(days=dagen_tot_zaterdag)

def send_telegram(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        data = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
        requests.post(url, data=data)
    except Exception as e:
        print(f"Fout bij sturen naar Telegram: {e}")

def get_weather():
    # We kijken 16 dagen vooruit om zeker te zijn dat het weekend erin valt
    url = f"https://api.open-meteo.com/v1/forecast?latitude={LOCATIE['lat']}&longitude={LOCATIE['lon']}&daily=temperature_2m_max,temperature_2m_min,snowfall_sum,precipitation_probability_max&timezone=Europe%2FBerlin&forecast_days=16"
    return requests.get(url).json()

def main():
    print("Seizoens-Agent gestart...")
    vandaag = datetime.date.today()

    # 1. Check of het seizoen voorbij is
    if vandaag > EINDE_SEIZOEN:
        print("Seizoen is afgelopen. Ik stop ermee.")
        return

    # 2. Bepaal doel datum (Aanstaande Zaterdag)
    target_date_obj = get_next_saturday()
    target_date_str = str(target_date_obj)
    
    # 3. Historie laden
    historie = []
    if os.path.exists(OPSLAG_BESTAND):
        with open(OPSLAG_BESTAND, 'r') as f:
            try: historie = json.load(f)
            except: historie = []

    # 4. Weer ophalen
    data = get_weather()
    if 'daily' not in data:
        send_telegram("⚠️ Fout bij ophalen weerdata.")
        return

    dagen = data['daily']['time']
    try:
        idx = dagen.index(target_date_str)
    except ValueError:
        print(f"Datum {target_date_str} buiten bereik API.")
        return

    # De voorspelling voor dat weekend
    nieuwe_check = {
        "datum_check": str(vandaag),
        "doel_datum": target_date_str,
        "max": data['daily']['temperature_2m_max'][idx],
        "min": data['daily']['temperature_2m_min'][idx],
        "sneeuw": data['daily']['snowfall_sum'][idx],
        "neerslag": data['daily']['precipitation_probability_max'][idx]
    }

    # 5. Trend Analyse (Vergelijk alleen met checks voor DEZELFDE doel datum)
    trend_msg = ""
    relevante_historie = [h for h in historie if h.get('doel_datum') == target_date_str]
    # Sorteer: nieuwste eerst
    relevante_historie = sorted(relevante_historie, key=lambda x: x['datum_check'], reverse=True)[:2]

    if relevante_historie:
        trend_msg = "\n📉 *Trend t.o.v. vorige check:*\n"
        vorige = relevante_historie[0] # De meest recente vorige check
        
        diff_temp = nieuwe_check['max'] - vorige['max']
        diff_snow = nieuwe_check['sneeuw'] - vorige['sneeuw']
        
        pijl_t = "🔺" if diff_temp > 0 else "🔻"
        pijl_s = "meer ❄️" if diff_snow > 0 else "minder ❄️"
        if diff_snow == 0: pijl_s = "stabiel"
        
        trend_msg += f"- Gisteren voorspeld: {vorige['max']}°C & {vorige['sneeuw']}cm\n"
        trend_msg += f"- Verschil: {abs(round(diff_temp,1))}°C {pijl_t} & {pijl_s}\n"

    # 6. Bericht sturen
    bericht = (f"🏔️ **Weekend Update**\n"
               f"📅 Voor zaterdag: {target_date_str}\n\n"
               f"🌡️ Max: {nieuwe_check['max']}°C (Min: {nieuwe_check['min']}°C)\n"
               f"❄️ Sneeuw: {nieuwe_check['sneeuw']} cm\n"
               f"☔ Neerslagkans: {nieuwe_check['neerslag']}%\n"
               f"{trend_msg}\n"
               f"🔗 [Officiële Status](https://www.skiliftkarussell.de/aktuell/)\n"
               f"🔗 [Bergfex Overzicht](https://www.skiliftkarussell.de/aktuell/lift-und-pisteninfo/)")
    
    print(bericht)
    send_telegram(bericht)

    # 7. Opslaan (Voeg toe aan historie)
    historie.append(nieuwe_check)
    # Houd het bestand klein: bewaar alleen de laatste 50 checks
    if len(historie) > 50:
        historie = historie[-50:]
        
    with open(OPSLAG_BESTAND, 'w') as f:
        json.dump(historie, f)

if __name__ == "__main__":
    main()
