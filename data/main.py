import requests
import time
import json
from datetime import datetime
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive

gauth = GoogleAuth()
drive = GoogleDrive(gauth)

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
    
    dt_update = datetime.fromtimestamp(r.json()["lastUpdatedOther"])
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

    while True:
        try:
            dlStationsStatus()
        except Exception as e:
            print(e)
        finally:
            now_tm = time.time()
            if mloop and (now_tm - start_tm)/60 < mloop:
                break;
            time.sleep(120)

def main():
    dlStationsInfo()
    loopDlStatus()

if __name__ == "__main__":
    main()
