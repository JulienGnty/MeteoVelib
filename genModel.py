import pandas as pd
import numpy as np
import random
import datasets as dst
import json
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, accuracy_score

import joblib

import conf as cf


def preProcessDataframe(df: object) -> object:
    dfret = df.dropna(subset = [
        "station_id", 
        "lat", 
        "lon", 
        "occupation_prct", 
        "occupation_class"
    ]).copy()
    
    return dfret

def splitDataframeTrainTest(file_list: list, step = 1) -> tuple:
    if len(file_list) > 14:
        file_list = file_list[-14:]

    df_train = dst.getDataset(file_list[0][-14:-4]).iloc[0::step]
    for file in file_list[1:(len(file_list) - 2)]:
        df_train = pd.concat([
            df_train,
            dst.getDataset(file[-14:-4]).iloc[0::step]
        ])

    df_test = dst.getDataset(file_list[-1][-14:-4]).iloc[0::step]

    return preProcessDataframe(df_train), preProcessDataframe(df_test)
    
def generateOneModel(df_train: object, df_test :object, station_id: int) -> object:

    feat = ["station_id", "lon", "lat", "year", "month", "day", "hour", "minute"]
    target = ["occupation_prct"]

    x_train = df_train[df_train['station_id'] == station_id][feat]
    y_train = df_train[df_train['station_id'] == station_id][target]
    
    x_test = df_test[df_test['station_id'] == station_id][feat]
    y_test = df_test[df_test['station_id'] == station_id][target]

    clf = GradientBoostingRegressor(random_state=0)
    clf.fit(x_train, y_train.values.ravel())

    y_pred = clf.predict(x_test)

    feat_importance = []

    for i in range(len(clf.feature_names_in_)):
        feat_importance.append([
            clf.feature_names_in_[i], clf.feature_importances_[i]
        ])

    model_dict = {
        "station_id": station_id,
        "file_name": "velib_model_" + str(station_id) + ".joblib.z",
        "mae": np.round(mean_absolute_error(y_test, y_pred), 2),
        "feat": feat,
        "target": target,
        "feature_importance": feat_importance,
        "data": {
            "time": df_test[df_test['station_id'] == station_id].time.dt.strftime("%Y-%m-%d %H:%M:%s").tolist(),
            "y_test": list(y_test["occupation_prct"]),
            "y_pred": list(y_pred),
        }
    }

    #print("mae:", model_dict["mae"])
    
    joblib.dump((clf), cf.DIRPATH + "model/" + model_dict["file_name"])

    return model_dict

def generateMultipleModel(count = 0, step = 1):
    df_train, df_test = splitDataframeTrainTest(dst.listDatasets(), step)

    station_list = list(set(dst.getStationsInfo().station_id))

    if count:
        station_list = random.sample(list(set(df_train.station_id)), count)

    model_list = []
    for station in station_list:
        model_list.append(generateOneModel(df_train, df_test, station))

    with open(cf.DIRPATH + "model/velib_model_list.json", "w") as outfile:
        json.dump(model_list, outfile)


if __name__ == "__main__":
    print(cf.DIRPATH)
    print("test")
    print(dst.listDatasets()[-1][-14:-4])
    generateMultipleModel(count = 700)
