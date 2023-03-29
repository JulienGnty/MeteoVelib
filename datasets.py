import requests
import json
import re
import datetime as dt
import numpy as np
import pandas as pd
import conf as cf
from glob import glob


def getStationsStatus(path_file: str) -> object:
    """
        Return a DataFrame object which contains all Stations Status at a particular time specified within path_file
    """

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

def getStationsInfo() -> object:
    """
        Return a DataFrame object which contains all stations informations (id, name, localisation and capacity)
    """
    info = pd.read_json(cf.DIRPATH + 'data/download/stations_info.json')
    data_info = pd.DataFrame(info.data.stations)
    
    alt_dict = {
        "station_id": [],
        "altitude": [],
    }
    with open(cf.DIRPATH + "data/download/altitude.json") as file:
        data_alt = json.load(file)

    print(type(data_alt))

    for key in data_alt.keys():
        alt_dict["station_id"].append(int(key))
        alt_dict["altitude"].append(float(data_alt[key]))

    df_alt = pd.DataFrame.from_dict(alt_dict)
    data_info = data_info.merge(df_alt, on = "station_id")
    
    feat = ["station_id", "stationCode", "name", "lon", "lat", "altitude", "capacity"]
    
    return data_info[feat]

def getWeatherData(day: str) -> object:
    """
        Return a DataFrame object which contains all eather data ot the chosen day
        'day' parameter should be a str in that format:
        %Y_%m_%d
    """
    weather_dict = {
        "year": [],
        "month": [],
        "day": [],
        "hour": [],
        "weather": [],
        "temperature": [],
        "humidity": [],
        "visibility": [],
        "wind_speed": [],
        "wind_deg": [],
        "clouds": [],
    }
    weather_files = glob(cf.DIRPATH + "data/download/weather_"+day+"_*.json")
    
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

    return pd.DataFrame.from_dict(weather_dict)

def getDataset(day: str) -> object:
    """
        Return a DataFrame object containing the data of the day chosen
        'day' parameter should be a str in that format:
        %Y_%m_%d
    """
    df = pd.read_csv(cf.DIRPATH + "data/datasets/stations_status_" + day + ".zip")
    df['time'] = pd.to_datetime(df['time'])
    df = df.drop(["Unnamed: 0"] , axis=1)
    return df

def setDataset(day: str, google = False):
    """
        Create a Dataset and save it in compressed file, for the day chosen
        'day' parameter should be a str in that format:
        %Y_%m_%d
        
        'google' paramater to define if it save the Dataset to the google drive
    """
    
    # Get all stations status of the day
    list_files = glob(cf.DIRPATH + "data/download/stations_status_"+day+"_*.json")

    df = getStationsStatus(list_files[0])
    for i in range(1,len(list_files)):
        dftemp = getStationsStatus(list_files[i])
        df = pd.concat([df, dftemp])

    # Merge with Weather Data
    df = df.merge(getWeatherData(day), on = ["year", "month", "day", "hour"])

    # Merge with Stations Informations
    df = df.merge(getStationsInfo(), on = "station_id")
    
    # Create two columns: occupation_prct and occupation_class
    df["occupation_prct"] = 100 * df["num_bikes_available"] / df["capacity"]
    conditions = [(df['occupation_prct'] < cf.LIMITS[0])]
    for i in range(len(cf.LIMITS)):
        if i == len(cf.LIMITS)-1:
            conditions.append((df['occupation_prct'] >= cf.LIMITS[i]))
        else:
            conditions.append((df['occupation_prct'] >= cf.LIMITS[i]) & (df['occupation_prct'] < cf.LIMITS[i+1]))
    values = [i for i in range(len(cf.LIMITS)+1)]
    df['occupation_class'] = np.select(conditions, values)

    # Compress and save the Dataframe into datasets folder
    compression_opts = dict(method = "zip", archive_name = "stations_status_"+day+".csv")
    df.to_csv(cf.DIRPATH + "data/datasets/stations_status_"+day+".zip",compression = compression_opts)
    
    print("Dataset created successfully")

    if google:
        file = drive.CreateFile({
            "title": "stations_status_"+day+".zip",
            "mimeType": "application/zip",
            "parents": [{"id": "1MFeACkAsxibfyoH_bviZPYXOZ16hoCgl"}]
        })
        file.SetContentFile(cf.DIRPATH + "data/datasets/stations_status_"+day+".zip")
        file.Upload()
        
        print("Dataset uploaded successfully")

def setDatasetV2(day: str, google = False):
    """
        Create a Dataset and save it in compressed file, for the day chosen
        'day' parameter should be a str in that format:
        %Y_%m_%d
        
        'google' paramater to define if it save the Dataset to the google drive
    """
    list_files_dl = []
    
    for i in range(24):
        # Get all stations status of the day
        list_files = glob(cf.DIRPATH + "data/download/stations_status_" + day + "_" + str(i).zfill(2) + "*.json")
        if len(list_files) == 0:
            continue
        data_per_hour = len(list_files)//4
        list_files_dl += list_files[0::data_per_hour + 1]

    df = getStationsStatus(list_files_dl[0])
    for i in range(1,len(list_files_dl)):
        dftemp = getStationsStatus(list_files_dl[i])
        df = pd.concat([df, dftemp])

    # Merge with Weather Data
    df = df.merge(getWeatherData(day), on = ["year", "month", "day", "hour"])

    # Merge with Stations Informations
    df = df.merge(getStationsInfo(), on = "station_id")

    STRIKE_DAYS = ["2023_03_23", "2023_03_28"]

    if day in STRIKE_DAYS:
        df["strike"] = 1
    else:
        df["strike"] = 0

    DEMONSTRATION_DAYS = ["2023_03_18", "2023_03_23", "2023_03_28"]

    if day in DEMONSTRATION_DAYS:
        df["demonstration"] = 1
    else:
        df["demonstration"] = 0
    
    # Create two columns: occupation_prct and occupation_class
    df["occupation_prct"] = 100 * df["num_bikes_available"] / df["capacity"]
    conditions = [(df['occupation_prct'] < cf.LIMITS[0])]
    for i in range(len(cf.LIMITS)):
        if i == len(cf.LIMITS)-1:
            conditions.append((df['occupation_prct'] >= cf.LIMITS[i]))
        else:
            conditions.append((df['occupation_prct'] >= cf.LIMITS[i]) & (df['occupation_prct'] < cf.LIMITS[i+1]))
    values = [i for i in range(len(cf.LIMITS)+1)]
    df['occupation_class'] = np.select(conditions, values)

    # Compress and save the Dataframe into datasets folder
    compression_opts = dict(method = "zip", archive_name = "stations_statusV2_"+day+".csv")
    df.to_csv(cf.DIRPATH + "data/datasets/stations_statusV2_"+day+".zip",compression = compression_opts)
    
    print("Dataset created successfully")

    if google:
        file = drive.CreateFile({
            "title": "stations_statusV2_"+day+".zip",
            "mimeType": "application/zip",
            "parents": [{"id": "1MFeACkAsxibfyoH_bviZPYXOZ16hoCgl"}]
        })
        file.SetContentFile(cf.DIRPATH + "data/datasets/stations_statusV2_"+day+".zip")
        file.Upload()
        
        print("Dataset uploaded successfully")
        

def listDatasets() -> list:
    return glob(cf.DIRPATH + "data/datasets/stations_status_*.zip")

if __name__ == "__main__":
    print(cf.DIRPATH + "data/download/stations_info.json")
    print(getStationsInfo())
    print(setDatasetV2("2023_03_28"))
