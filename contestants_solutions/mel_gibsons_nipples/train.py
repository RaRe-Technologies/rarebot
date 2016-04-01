# Author: Josef Samanek, 139911

import sys
import json
import datetime
from collections import OrderedDict

from sklearn import preprocessing
from sklearn import svm

import pickle

import os

#import numpy as np

#import matplotlib.pyplot as plt
#from matplotlib import style
#style.use("ggplot")
#from sklearn.decomposition import PCA

# pripravi data do potrebneho formatu (multidimenzionalniho pole), z nehoz jde rovnou vytvorit napr. pandas.DataFrame nebo numpy.array, pripadne i rovnou pouzit v mnoha sklearn algoritmech
# vraci dvojici: data (dict by user), dataValues (value -> number mappings)
def prepDataByUser(logFile):
    data = {}
    # does it have to be ordered ???
    #dataValues = OrderedDict( [ ('category', []), ('behaviour', []), ('connection', []), ('user', []), ('day', []), ('time', []), ('safe_connection', []) ] )
    dataValues = OrderedDict( [ ('category', []), ('behaviour', []), ('connection', []), ('safe_connection', []) ] )
    #dataValues = OrderedDict( [ ('category', []), ('behaviour', []), ('region', []), ('country', []), ('city', []), ('safe_connection', []) ] )
    with open(logFile) as data_file:
        for line in data_file:
            lineDict = json.loads(line, object_pairs_hook=OrderedDict) # bez OrderedDict by to pokazde hazelo jine poradi atributu
            templist = []

            if lineDict['user'] not in data:
                data[lineDict['user']] = []
            
            for key, value in lineDict.items():
                if key == 'user':
                    continue
                if key == 'is_anomaly':
                    continue

                if key == 'unix_timestamp':
                    day = datetime.datetime.fromtimestamp(value).weekday()
                    time = datetime.datetime.fromtimestamp(value).time()
                    seconds = time.hour*3600 + time.minute*60 + time.second
                    templist.append(day)
                    templist.append(seconds)
                    #templist.append(time.hour)
                    continue

                '''
                # pokus o rozdeleni connection na 3 atributy region, country, city. Po prvnim kratkem otestovani to prekvapive hazelo horsi vysledky
                if key == 'connection':
                    region, country, city = value.split('-', 2)

                    valueInt = 0                    
                    # pokud jsme jiz na danou hodnotu drive narazili, zapiseme to same cislo 
                    if region in dataValues['region']:
                        valueInt = dataValues['region'].index(region)
                    # jinak zapiseme nejnizsi nepouzite cislo, resp. delku seznamu jiz najitych unikatnich hodnot
                    else:
                        valueInt = len(dataValues['region'])
                        dataValues['region'].append(region)
                    templist.append(valueInt)

                    valueInt = 0                    
                    # pokud jsme jiz na danou hodnotu drive narazili, zapiseme to same cislo 
                    if country in dataValues['country']:
                        valueInt = dataValues['country'].index(country)
                    # jinak zapiseme nejnizsi nepouzite cislo, resp. delku seznamu jiz najitych unikatnich hodnot
                    else:
                        valueInt = len(dataValues['country'])
                        dataValues['country'].append(country)
                    templist.append(valueInt)

                    valueInt = 0                    
                    # pokud jsme jiz na danou hodnotu drive narazili, zapiseme to same cislo 
                    if city in dataValues['city']:
                        valueInt = dataValues['city'].index(city)
                    # jinak zapiseme nejnizsi nepouzite cislo, resp. delku seznamu jiz najitych unikatnich hodnot
                    else:
                        valueInt = len(dataValues['city'])
                        dataValues['city'].append(city)
                    templist.append(valueInt)                    
                    continue
                '''
                
                # pokud jsme jiz na danou hodnotu drive narazili, zapiseme to same cislo
                valueInt = 0
                if value in dataValues[key]:
                    valueInt = dataValues[key].index(value)
                # jinak zapiseme nejnizsi nepouzite cislo, resp. delku seznamu jiz najitych unikatnich hodnot
                else:
                    valueInt = len(dataValues[key])
                    dataValues[key].append(value)                    
                templist.append(valueInt)
                
            data[lineDict['user']].append(templist)
    return data, dataValues

# pomocna fce k pokusu o vyuziti one-hot kodovani (DictVectorizer) vyctovych atributu, prozatim nevyuzito (30.3.2016 23:00)
def prepDataByUserForDictVect(logFile):
    data = {}
    with open(logFile) as data_file:
        for line in data_file:
            #lineDict = json.loads(line, object_pairs_hook=OrderedDict) # bez OrderedDict by to pokazde hazelo jine poradi atributu
            lineDict = json.loads(line)
            tempDict = {}

            if lineDict['user'] not in data:
                data[lineDict['user']] = []
            
            for key, value in lineDict.items():
                if key == 'user':
                    continue
                if key == 'is_anomaly':
                    continue # vyskytuje se pouze v short_test.log, takze nema smysl zapisovat

                if key == 'unix_timestamp': # z timestamp jsem udelal 2 atributy - den v tydnu a cas; zbytek myslim neni prilis podstatny
                    day = datetime.datetime.fromtimestamp(value).weekday()
                    time = datetime.datetime.fromtimestamp(value).time()
                    tempDict['day'] = day
                    tempDict['hour'] = time.hour
                    continue
                
                if key == 'connection':
                    region, country, city = value.split('-', 2)
                    tempDict['region'] = region
                    tempDict['country'] = country
                    tempDict['city'] = city                  
                    continue
                
                tempDict[key] = value
                
            data[lineDict['user']].append(tempDict)
    return data

def main(argv):
    log_file = ""
    try:
        log_file = argv[0]
    except IndexError:
        #log_file = './competition_train_round1.log'
        print("Missing argument: path to training data file")
        sys.exit(1)

    print('Preparing data')            
    dataByUser, mappings = prepDataByUser(log_file)
    #testDataByUser, mappings2 = prepDataByUser(test_file)

    predictions = {}
    models = {}   
    users = []
    for user, data in dataByUser.items():
        print 'Training model and scaler for', user
        users.append(user)
        scaler = preprocessing.StandardScaler().fit(data)
        dataNorm = scaler.transform(data)

        clf = svm.OneClassSVM(nu=0.0225, kernel="rbf", gamma=0.1) # F-measure = 0.266448
		
        clf.fit(dataNorm)

        models[user] = clf

        # save scaler
        filename = user +  "_scaler.pkl"
        with open(filename, 'wb') as file:
            pickle.dump(scaler, file, protocol = 2)
           
        # uncomment to view graphed plots (together with line #194 + add test_file)
        """
        testDataNorm = scaler.transform(testDataByUser[user])
        trainReduced = PCA(n_components = 2).fit_transform(dataNorm)
        testReduced = PCA(n_components = 2).fit_transform(testDataNorm)
        #predictions[user] = clf.predict(testDataNorm)

        plt.title(user)
        plt.scatter(testReduced[:, 0], testReduced[:, 1], c='green')
        plt.scatter(trainReduced[:, 0], trainReduced[:, 1], c='black')
        plt.show()
        """

    print('Saving value mappings')
    # save value mappings
    filename = "mappings.pkl"
    with open(filename, 'wb') as mapFile:
        pickle.dump(mappings, mapFile, protocol = 2)

    print('Saving list of users')
    # save users
    filename = "users.pkl"
    with open(filename, 'wb') as usersFile:
        pickle.dump(users, usersFile, protocol = 2)

    print('Saving models')
    # save models
    for user, clf in models.items():
        filename = user +  ".pkl"
        with open(filename, 'wb') as file:
            pickle.dump(clf, file, protocol = 2)
        
    print('Done')

if __name__ == '__main__':
    main(sys.argv[1:])
