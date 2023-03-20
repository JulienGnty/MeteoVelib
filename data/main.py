import requests
import time
import json
import re
import datetime as dt
import pandas as pd
from glob import glob
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive

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
    data['hour'] = date.time()

    return data

def setDataset(day: str):
    list_files = glob("download/stations_status_"+day+"_*.json")

    df = read_data(list_files[0])
    for i in range(1,len(list_files)):
        dftemp = read_data(list_files[i])
        df = pd.concat([df, dftemp])

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

    file = drive.CreateFile({
        "title": "stations_status"+str_update+".json",
        "mimeType": "application/json",
        "parents": [{"id": "18x6j09DVTGBNaatYAEoN3ErPwNf250fy"}]
    })
    file.SetContentFile("download/stations_status"+str_update+".json")
    file.Upload()

def loopDlStatus(mloop = 0):
    """
        Starts a loop to download data for mloop minutes

        If mloop = 0 (default value), it starts infinite loop
    """
    start_tm = time.time()
    start_date = dt.date.today()

    while True:
        try:
            dlStationsStatus()
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
