# Projet MétéoVélib

Développé par:
- Julien GENETY: https://github.com/JulienGnty/
- Olivier FLOYD: https://github.com/OFloyd/

MétéoVélib est une application qui propose à un utilisateur une prédiction dans un futur proche, de la disponibilité des vélos du système de vélos en libre-service appelé "Vélib" disponible à Paris et quelques communes de l'agglomération parisienne.

## Installation

### Pré-requis

Pour l'ensemble du projet, il faut __Python__ version __3.8.\*__, __3.9.\*__ ou __3.10.\*__ et un accès à Internet.
Pour la partie extraction de données, il faut une __clé de connexion à l'api de OpenWeatherMap__ et __5 Go d'espace sur le disque dur__ par semaine de stockage de données (pour plus de détails, voir partie Fonctionnement - Extraction de données).

### Configuration de l'environnement

Après avoir clôné ce dépôt, il faut modifier dans le fichier conf.py:
- DIRPATH est le chemin absolu du projet sur la machine sur laquelle vous l'installez
- KEY est la clé de connexion à l'api de OpenWeatherMap

Par contre, LAT, LON et LIMITS n'ont pas besoin d'être modifiés.

Ensuite il faut créer l'environnement virtuel du projet. Ouvrez l'invite de commande et exécutez cette instruction:
```
python -m venv velibenv
```

Activez ensuite l'environnement en exécutant cette instruction pour Windows:
```
velibenv\Scripts\activate
```
Ou cette instruction pour Linux et Mac:
```
source velibenv/bin/activate
```

Enfin il faut installer, dans l'environnement virtuel, les librairies requises pour le fonctionnement du projet:
```
pip install -r requirements.txt
```

## Lancement

### Application

La partie applicative se lance en exécutant le code du fichier app.py comme ceci:
```
python app.py
```
Ce code ouvre un serveur Flask en local, sur le port 5000. On peut donc accéder à l'application en allant sur cette adresse sur un navigateur web:
```
http://127.0.0.1:5000/
```

### Extraction de données

L'extraction de données se fait en continu en exécuant le fichier main.py:
```
python main.py
```
Ce code source tourne en boucle et télécharge:
- toutes les 2 minutes l'état des stations Vélib, depuis l'OpenData Vélib
- toutes les heures les données météo depuis l'api de OpenWeatherMap
- tous les jours, les informations statiques relatives aux stations Vélib (nom, emplacement, capacité) depuis l'OpenDataVélib
Chaque jour à minuit, ce code agrève l'ensemble de ces données téléchargées durant la journée pour créer et enregistrer un ensemble de données "Dataset".

## Fonctionnement

Ce projet contient 3 modules principaux exécutables:
- main.py -> gère l'extraction de données
- app.py -> lance l'application web
- genModel.py -> génère les modèles de prédiction

Un 4ème module, datasets.py, est régulièrement appelé par les autres modules. Il contient l'ensemble des fonctions permettant de générer, de lister et de charger les ensembles de données disponibles.

### Extraction de données

Ce dépôt GitHub contenant déjà des données de bases pour exécuter l'application et générer des modèles de prédiction, il est tout à fait possible d'ignorer cette partie-là et la configuration nécessaire pour le faire tourner. Cependant, votre application et votre générateur de modèles fonctionneront sur des données qui ne seront pas actualisées.

#### Vélib OpenData

La source principale de données de ce programme est l'OpenData de Vélib: https://www.velib-metropole.fr/donnees-open-data-gbfs-du-service-velib-metropole

Cette source propose 2 flux de données importants:
- les caractéristiques et localisations des 1472 stations vélib qu'on appelle communément "station information" dans ce projet; ces données sont en format json et ont tendance à peu changer au cours du temps. En effet, des stations ne sont pas rajoutées ou retirées tous les jours dans Paris, leur capacité ne change pas souvent non plus et elles ne sont pas renommées régulièrement. On capte donc cette source __1 fois par jour, vers minuit__. Les données sont enregistrées dans le fichier __station\_information.json__ dans le dossier data/download.
- le nombre de vélos et de bornettes disponibles par station qu'on appelle communément "station status"; ces données sont en format json et réflètent à l'instant T l'état des stations, le nombre de vélos qu'elle contienne, le type de ces vélos (éléctrique ou mécanique), savoir si la station est actuellement en maintenance ou pas. Ces données sont mises à jour toutes les minutes par Vélib et sont captées __toutes les 2 minutes__ dans ce projet. Ces données sont enregistrées dans un fichier __station\_station\__date_.json__ dans le dossier data/download. _date_ représente la date à laquelle ces données ont été générées (exemple: 2023_03_31_14_28_35 pour un fichier généré le 31 Mars 2023 à 14:28:35).

#### OpenWeatherMap

La 2nde source de données du programme est l'api d'OpenWeatherMap: https://openweathermap.org/api

Cette api propose, dans sa version gratuite, un nombre limité de requêtes permettant d'avoir à l'instant T les données météo de la ville de Paris: température, humidity, force et direction du vent, etc... Ces données sont récupérées toutes les heures et enregistrées dans un fichier __weather\__date_.json__ dans le dossier data/download. _date_ représente la date à laquelle ces données ont été générées (exemple: 2023_03_31_14 pour un fichier généré le 31 Mars 2023 à 14:00:00)

#### Construction d'un ensemble de données

Chaque jour après minuit, le main.py lance la construction d'un dataset qui récupère tous les fichiers générés la veille et agrège tous ces données ensemble. Ce dataset est construit à l'aide de la bibliothèque pandas, est compressé au format .zip et est enregistré dans le dossier data/datasets.

Un dataset sur une journée sans problème, contient environ 1 million de lignes et 30 colonnes, avec environ 30 lignes de données par heure et par station. Une seconde version de Dataset nommée "V2" a été créée et ne contient que 4 lignes de données par heure et par station.

#### Gestion du stockage

L'enregistrement des "station status" peut poser problème à terme. Chacun de ces fichiers fait quasiment 1 Mo, et il y en a environ 720 générés par jour. Au bout d'une semaine, la charge monte à 5 Go. Il faut donc faire attention à l'espace disponible si vous comptez faire tourner l'extraction de données sur une longue période.

Cependant, il est tout à fait possible de supprimer ces fichiers d'une journée où le dataset a déjà été construit. Le dataset contenant déjà toutes les données, le station status n'est plus nécessaire.

### Modèles de prédiction

Pour construire le modèle de prédiction de la disponibilité des vélos, on s'est basé sur une intuition d'usager régulier du vélib: on constate chaque jour les même stations en pénurie ou en surcharge de vélo, et donc s'il existe bien un cycle d'usage des vélibs, on pourrait prédire la disponibilité des jours suivantes.

Cette intuition est également renforcée par cet article de Datascientist sur un sujet très similaire:
https://towardsdatascience.com/time-series-forecasting-with-machine-learning-b3072a5b44ba

On part donc sur l'hypothèse qu'il est possible de prédire la disponibilité en se basant sur la cyclicité de l'usage des vélibs et sur les paramètres extérieur qui font légèrement dévier ce cycle (météo, grèves et manifestations essentiellement).

__Pour plus d'infos et de détails sur cette partie, consultez le classeur jupyter presentation_machine_learning.ipynb__

#### Générateur de modèles

La génération des modèles de prédiction se fait à l'aide du module genModel.py. Ce module génère un modèle pour chaque station vélib, et enregistre tous ces modèles dans le dossier model. Le fichier _velib\_model\list.json_ contient un dictionnaire indiquant pour chaque station les caractéristiques du modèle de prédiction dont une métrique "mae" qui permet d'évaluer la qualité de la précision de ce modèle.

### Application

Cette application se base sur la librairie Flask et crée une interface web où un utilisateur peut faire une requête de disponibilité des vélibs pour une date donnée et un emplacement géolocalisé avce latitude et longitude. L'application renvoie ensuite la prédiction pour les stations de vélibs disponibles à moins de 500m de cet emplacement.

Pour chaque station vélib, l'application va télécharger le modèle correspondant dans le dossier model, et restituer le résultat à l'aide d'une carte générée par la librairie folium qui se base sur OpenStreetMap.
