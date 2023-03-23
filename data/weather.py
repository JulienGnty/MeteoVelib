import requests
import time
import json
import re
import datetime as dt
import conf as cf

def dlWeather():
    """
        Download current Weather data from OpenWeatherMap
    """
    base_url = f"https://api.openweathermap.org/data/2.5/weather?lat={cf.LAT}&lon={cf.LON}&appid={cf.KEY}"
    response = requests.get(base_url)

    data_dict = response.json()
    
    dt_update = dt.datetime.now()
    y, m, d, h = (
        str(dt_update.year),
        str(dt_update.month).zfill(2),
        str(dt_update.day).zfill(2),
        str(dt_update.hour).zfill(2)
    )
    str_update = "_" + y + "_" + m + "_" + d + "_" + h

    data_dict["time"] = { 
        "year": dt_update.year,
        "month": dt_update.month,
        "day": dt_update.day,
        "hour": dt_update.hour,
    }
    
    with open("download/weather"+str_update+".json", "w") as outfile:
        json.dump(data_dict, outfile)
        
    print("Current Weather (updated at ", dt_update, ") downloaded successfully", sep="")

def loopDlStatus():
    """
        Starts a loop to download current weather data
    """
    
    consecutive_errors = 0

    while True:
        start_tm = time.time()
        try:
            if consecutive_errors >= 10:
                return None
            dlWeather()
        except Exception as e:
            consecutive_errors += 1
            print(e)
            start_tm += 120
            time.sleep(120)
        else:
            consecutive_errors = 0
            now_tm = time.time()
            time.sleep(3600 - (now_tm - start_tm))

def main():
    loopDlStatus()

if __name__ == "__main__":
    main()
