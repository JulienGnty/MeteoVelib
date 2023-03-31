import pandas as pd
import numpy as np
import random
import datasets as dst
import json
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, accuracy_score

import joblib

import conf as cf

FEAT = [
    "temperature", 
    "humidity", 
    "wind_speed", 
    "strike", 
    "demonstration", 
    "weekday",
    "year",
    "month",
    "day", 
    "hour",
    "minute", 
]
TARGET = ["occupation_prct"]

VERSION = "V2"

def preProcessDataframe(df: object) -> object:
    """
        Delete rows with null values on columns needed as features or target
    """
    dfret = df.dropna(subset = FEAT + TARGET).copy()
    
    return dfret

def splitDataframeTrainTest(file_list: list, test_days = 7, limit = 28, step = 1) -> tuple:
    """
        Split data train and data test in chronological order.

        Parameters:
        - file_list: the paths list of files containing the data; file_list must be sorted in chronological order
        - test_days: the latest days used as data test; other days will be used as data train
        - limit, default to 28: select only the 'limit' last files
        - step, default to 1: select only one row on 'step' rows
    """
    if len(file_list) > limit:
        file_list = file_list[-limit:]

    train_list = file_list[:(len(file_list)-test_days)]
    test_list = file_list[-test_days:]

    df_train = dst.getDataset(train_list[0][-14:-4], version = VERSION).iloc[0::step]
    for file in train_list[1:]:
        df_train = pd.concat([
            df_train,
            dst.getDataset(file[-14:-4], version = VERSION).iloc[0::step]
        ])

    df_test = dst.getDataset(test_list[0][-14:-4], version = VERSION).iloc[0::step]
    for file in test_list[1:]:
        df_test = pd.concat([
            df_test,
            dst.getDataset(file[-14:-4], version = VERSION).iloc[0::step]
        ])

    return preProcessDataframe(df_train), preProcessDataframe(df_test)
    
def generateOneModel(df_train: object, df_test :object, station_id: int) -> object:
    """
        Generate a predidction model based on GradientBoostingRegressor
        Dump the model into a compressed file with joblib
        Save model informations in a dict which is returned
    """

    x_train = df_train[df_train['station_id'] == station_id][FEAT]
    y_train = df_train[df_train['station_id'] == station_id][TARGET]
    
    x_test = df_test[df_test['station_id'] == station_id][FEAT]
    y_test = df_test[df_test['station_id'] == station_id][TARGET]

    # Can't fit the model if data are empty
    if x_train.empty or y_train.empty or x_test.empty or y_test.empty:
        return 0

    clf = GradientBoostingRegressor(random_state = 42)

    clf.fit(x_train, y_train.values.ravel())

    y_pred = clf.predict(x_test)

    feat_importance = []

    for i in range(len(clf.feature_names_in_)):
        feat_importance.append([
            clf.feature_names_in_[i], clf.feature_importances_[i]
        ])

    model_dict = {
        "file_name": "velib_model_" + str(station_id) + ".joblib.z",
        "mae": np.round(mean_absolute_error(y_test, y_pred), 2),
        "feat": FEAT,
        "target": TARGET,
        "feature_importance": feat_importance,
    }

    print("mae:", model_dict["mae"])
    
    joblib.dump((clf), cf.DIRPATH + "model/" + model_dict["file_name"])

    return model_dict

def generateMultipleModel(count = 0, step = 1):
    """
        Generate several model. Each model is linked to a specific station
        If count, it takes 'count' random stations to generate model on it
        Else, it generates models on all stations
    """
    df_train, df_test = splitDataframeTrainTest(dst.listDatasets(version = VERSION), test_days = 5, step = step)

    station_list = list(set(dst.getStationsInfo().station_id))

    if count:
        station_list = random.sample(list(set(df_train.station_id)), count)

    model_list = {}
    for station in station_list:
        model_list[str(station)] = generateOneModel(df_train, df_test, station)

    with open(cf.DIRPATH + "model/velib_model_list.json", "w") as outfile:
        json.dump(model_list, outfile)


if __name__ == "__main__":
    generateMultipleModel()
