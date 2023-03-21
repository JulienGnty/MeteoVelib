import pandas as pd
from glob import glob

def getDataset(day: str) -> object:
    """
        Return a DataFrame object containing the data of the day chosen
        'day' parameter should be a str in that format:
        %Y_%m_%d
    """
    df = pd.read_csv("data/datasets/stations_status_" + day + ".zip")
    df['time'] = pd.to_datetime(df['time'])
    df = df.drop(["Unnamed: 0"] , axis=1)
    return df

def listDatasets() -> list:
    return glob("data/datasets/stations_status_*.zip")
