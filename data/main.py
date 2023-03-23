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

LIMITS = [5,25,75,95]

gauth = GoogleAuth()
drive = GoogleDrive(gauth)

# Fonction pour lire et formater un fichier à partir de son chemin d'accès
def read_data(path_file: str) -> object:

    #Reads the dataframe in the input file
    data0 = pd.read_json(path_file)
    data = pd.DataFrame(data0.data.stations)
    data.insert(3, 'num_bikes_available_mech', data.num_bikes_available_types.apply(lambda x: x[0].get('mechanical')) )
    data.insert(4, 'num_bikes_available_elec', data.num_bikes_available_types.apply(lambda x: x[1].get('ebike')) )

    #Removes the dupe columns
    data = data.drop(['numBikesAvailable','numDocksAvailable','stationCode','num_bikes_available_types'] , axis=1)

    #Determines the time the data was obtained
    date_str = re.search(r"\d{4}(_\d{2}){5}",path_file).group(0)
    date = dt.datetime.strptime(date_str, '%Y_%m_%d_%H_%M_%S')

    #Adds a field for the time
    data['time'] = date
    data['weekday'] = date.weekday()
    data['year'] = data["time"].dt.year
    data['month'] = data["time"].dt.month
    data['day'] = data["time"].dt.day
    data['hour'] = data["time"].dt.hour
    data['minute'] = data["time"].dt.minute

    return data

def setDataset(day: str):
    list_files = glob("download/stations_status_"+day+"_*.json")

    df = read_data(list_files[0])
    for i in range(1,len(list_files)):
        dftemp = read_data(list_files[i])
        df = pd.concat([df, dftemp])

    weather_dict = {
        "weather": [],
        "temperature": [],
        "humidity": [],
        "visibility": [],
        "wind_speed": [],
        "wind_deg": [],
        "clouds": [],
        "year": [],
        "month": [],
        "day": [],
        "hour": [],
    }
    weather_files = glob("download/weather_"+day+"_*.json")
    
    for file in weather_files:
        f = open(file)
        data = json.load(f)
        weather_dict["weather"].append(data["weather"][0]["main"])
        weather_dict["temperature"].append(data["main"]["temp"])
        weather_dict["humidity"].append(data["main"]["humidity"])
        weather_dict["visibility"].append(data["visibility"])
        weather_dict["wind_speed"].append(data["wind"]["speed"])
        weather_dict["wind_deg"].append(data["wind"]["deg"])
        weather_dict["clouds"].append(data["clouds"]["all"])
        weather_dict["year"].append(data["time"]["year"])
        weather_dict["month"].append(data["time"]["month"])
        weather_dict["day"].append(data["time"]["day"])
        weather_dict["hour"].append(data["time"]["hour"])

    df_weather = pd.DataFrame.from_dict(weather_dict)

    df = df.merge(df_weather, on = ["year", "month", "day", "hour"])

    # Read the information of each station (name, location, capacity)
    info = pd.read_json('download/stations_info.json')
    data_info = pd.DataFrame(info.data.stations)

    df = df.merge(data_info, on = "station_id").drop(["rental_methods", "stationCode"] , axis=1)
    df["occupation_prct"] = 100 * df["num_bikes_available"] / df["capacity"]

    conditions = [(df['occupation_prct'] < LIMITS[0])]

    for i in range(len(LIMITS)):
        if i == len(LIMITS)-1:
            conditions.append((df['occupation_prct'] >= LIMITS[i]))
        else:
            conditions.append((df['occupation_prct'] >= LIMITS[i]) & (df['occupation_prct'] < LIMITS[i+1]))

    # create a list of the values we want to assign for each condition
    values = [i for i in range(len(LIMITS)+1)]

    # create a new column and use np.select to assign values to it using our lists as arguments
    df['occupation_class'] = np.select(conditions, values)

    compression_opts = dict(method = "zip", archive_name = "stations_status_"+day+".csv")
    df.to_csv("datasets/stations_status_"+day+".zip",compression = compression_opts)

    file = drive.CreateFile({
        "title": "stations_status_"+day+".zip",
        "mimeType": "application/zip",
        "parents": [{"id": "1MFeACkAsxibfyoH_bviZPYXOZ16hoCgl"}]
    })
    file.SetContentFile("datasets/stations_status_"+day+".zip")
    file.Upload()

    print("Dataset uploaded successfully")

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

def dlStationsInfo():
    """
        Download stations informations from Velib OpenData
    """
    r = requests.get("https://velib-metropole-opendata.smoove.pro/opendata/Velib_Metropole/station_information.json",
                     headers = {"Accept": "application/json"})

    json_object = json.dumps(r.json(), indent=4)

    with open("download/stations_info.json", "w") as outfile:
        outfile.write(json_object)

    print("Stations Informations downloaded successfully")

def dlStationsStatus():
    """
        Download stations status from Velib OpenData
    """
    r = requests.get("https://velib-metropole-opendata.smoove.pro/opendata/Velib_Metropole/station_status.json",
                     headers = {"Accept": "application/json"})
    
    dt_update = dt.datetime.fromtimestamp(r.json()["lastUpdatedOther"])
    str_update = "_"+str(dt_update).replace("-","_").replace(" ","_").replace(":","_")
    
    json_object = json.dumps(r.json(), indent=4)
    
    with open("download/stations_status"+str_update+".json", "w") as outfile:
        outfile.write(json_object)
        
    print("Stations Status (updated at ", dt_update, ") downloaded successfully", sep="")

    """ DISABLED - TO UPLOAD ON GOOGLE DRIVE
    file = drive.CreateFile({
        "title": "stations_status"+str_update+".json",
        "mimeType": "application/json",
        "parents": [{"id": "18x6j09DVTGBNaatYAEoN3ErPwNf250fy"}]
    })
    file.SetContentFile("download/stations_status"+str_update+".json")
    file.Upload()
    """

def loopDlStatus(mloop = 0):
    """
        Starts a loop to download data for mloop minutes

        If mloop = 0 (default value), it starts infinite loop
    """
    # Used for mloop
    start_tm = time.time()

    # Used for setting Datasat at midnight
    start_date = dt.date.today()

    # Used for downloading current weather every hour
    weather_date = dt.datetime.now()

    while True:
        try:
            dlStationsStatus()
            
            now_dt = dt.datetime.now()
            if weather_date.hour != now_dt.hour and now_dt.minute > 20:
                dlWeather()
                weather_date = now_dt           
        except Exception as e:
            print(e)
        finally:            
            now_tm = time.time()            
            if mloop and (now_tm - start_tm)/60 < mloop:
                break;
            
            now_date = dt.date.today()
            if start_date != now_date:
                start_date = now_date
                yesterday = start_date - dt.timedelta(days = 1)
                setDataset(str(yesterday).replace("-","_"))

            time.sleep(120)

def main():
    dlStationsInfo()
    loopDlStatus()

if __name__ == "__main__":
    main()
