import requests
import time
import json
import re
import datetime as dt
import pandas as pd
import numpy as np
import conf as cf
from glob import glob
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
import datasets as dst

LIMITS = [5,25,75,95]

gauth = GoogleAuth()
drive = GoogleDrive(gauth)

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
    
    with open(cf.DIRPATH + "data/download/weather"+str_update+".json", "w") as outfile:
        json.dump(data_dict, outfile)
        
    print("Current Weather (updated at ", dt_update, ") downloaded successfully", sep="")

def dlStationsInfo():
    """
        Download stations informations from Velib OpenData
    """
    r = requests.get("https://velib-metropole-opendata.smoove.pro/opendata/Velib_Metropole/station_information.json",
                     headers = {"Accept": "application/json"})

    json_object = json.dumps(r.json(), indent=4)

    with open(cf.DIRPATH + "data/download/stations_info.json", "w") as outfile:
        outfile.write(json_object)

    print("Stations Informations downloaded successfully")

def dlStationsStatus(google = False):
    """
        Download stations status from Velib OpenData
    """
    r = requests.get("https://velib-metropole-opendata.smoove.pro/opendata/Velib_Metropole/station_status.json",
                     headers = {"Accept": "application/json"})
    
    dt_update = dt.datetime.fromtimestamp(r.json()["lastUpdatedOther"])
    str_update = "_"+str(dt_update).replace("-","_").replace(" ","_").replace(":","_")
    
    json_object = json.dumps(r.json(), indent=4)
    
    with open(cf.DIRPATH + "data/download/stations_status"+str_update+".json", "w") as outfile:
        outfile.write(json_object)
        
    print("Stations Status (updated at ", dt_update, ") downloaded successfully", sep="")

    if google:
        file = drive.CreateFile({
            "title": "stations_status"+str_update+".json",
            "mimeType": "application/json",
            "parents": [{"id": "18x6j09DVTGBNaatYAEoN3ErPwNf250fy"}]
        })
        file.SetContentFile(cf.DIRPATH + "data/download/stations_status"+str_update+".json")
        file.Upload()
        
        print("File uploaded successfully")


def loopDlStatus(info = True, status = True, weather = True, dataset = True):
    """
        Starts a loop to download data.
        Paramaters:
        - info: default True; If True, this function loads station_informations.json at midnight
        - status: default True; If True, this function loads station_status.json every 2 minutes
        - weather: default True; If True, this function loads weather from OpenWeatherMap every hour
        - dataset: default True; If True, this function creates Dataset of the last day at midnight    
    """
    info_dl = info
    status_dl = status
    weather_dl = weather
    create_dataset = False

    last_dt = dt.datetime.now()

    while True:
        now_dt = dt.datetime.now()

        if last_dt.day != now_dt.day:
            info_dl = info
            create_dataset = dataset
        
        if last_dt.hour != now_dt.hour:
            weather_dl = weather
            
        last_dt = now_dt
        
        if info_dl:
            try:
                dlStationsInfo()
            except Exception as e:
                print("Error with stations informations download")
                print(e)
            else:
                info_dl = False
                
        if status_dl:
            try:
                dlStationsStatus()         
            except Exception as e:
                print("Error with stations status download")
                print(e)

        if weather_dl:
            try:
                dlWeather()
            except Exception as e:
                print("Error with weather data download")
                print(e)
            else:
                weather_dl = False

        if create_dataset:
            try:
                yesterday = dt.date.today() - dt.timedelta(days = 1)
                dst.setDataset(str(yesterday).replace("-","_"))
            except Exception as e:
                print("Error with creation of Dataset for " + str(yesterday).replace("-","_"))
                print(e)
            else:
                create_dataset = False
                # To skip the time sleep, because this part is very long
                continue
        
        time.sleep(120)

def main():    
    loopDlStatus()

if __name__ == "__main__":
    main()
