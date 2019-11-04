import serial
from datetime import datetime
import time
import numpy as np
import configparser  #Module pour gérer l import d un fichier de configuration
import argparse #Module pour ajouter des paramètres lors de l appel du script 
from influxdb import InfluxDBClient  #Module pour gérer l export des données vers la base InfluxDB
import os
sensor='SDS011'


#############################################
#############################################
#INFO A REMPLIR AVANT LANCEMENT DU FICHIER

port = '/dev/ttyUSB0'
nom_fichier = 'airbeam.txt'
moyenne=10
num_serie_capteur = '1234'
site='Grenoble les frene'


###########################################
#############################################



class SDS011:


#Fonction d'initialisation 
    def __init__(self,port = port):
        self.port = port


#Fonction pour acquerir les donnees     
    def acquisition(self):
        "Acquisition donn�es PM2.5 et PM10 depuis un SDS011"
        capteur = serial.Serial(self.port)
        #print(capteur)
        byte = capteur.read()
        #print(byte)
        if byte == b'\xaa':
            sentence = capteur.read(size=9) # Read 8 more bytes
            PM25= (sentence[1]+sentence[2])/10
            PM10 = (sentence[3]+sentence[4])/10
            line = "  PM 2.5: {} μg.m-3  PM 10: {} μg.m-3".format(PM25, PM10)
            # ignoring the checksum and message tail
            print(datetime.now().strftime("%Y/%m/%d %H:%M:%S")+line)
            return {
                "tags":{
                    "sensor": "SDS011"},
                "fields":{
                    "PM2.5":PM25,
                    "PM10":PM10}
                    }
        else:
            print("En attente de données valides ")
            return {"tags":{
                    "sensor": "SDS011"},
                "fields":{
                    "PM2.5":'',
                    "PM10":''}
                    }
                    
                    
                    
#Fonction pour le calcul de la moyenne     
    def moyenne(self,sample):
        i=0
        PM25list = list()
        PM10list = list()
        while i<=sample:
            res = self.acquisition()
            if res["fields"]["PM2.5"] !='': PM25list.append(res["fields"]["PM2.5"])
            if res["fields"]["PM10"] !='': PM10list.append(res["fields"]["PM10"])
            i+=1
        PM25res = np.array(PM25list)
        PM25mean = PM25res.mean()  #Moyenne PM25
        PM10res = np.array(PM10list)
        PM10mean = PM10res.mean()  #Moyenne PM10

        print('\n')
        print("----")
        print("{}: Moyenne : PM2.5 {} , PM10 {}".format(datetime.now().strftime("%d %b %Y %H:%M:%S"),round(PM25mean,3),round(PM10mean,3)))
        print("----")
        print('\n')
        test_var="{}; PM2.5; {} ; PM10; {}".format(datetime.now().strftime("%Y/%m/%d %H:%M:%S"),round(PM25mean,3),round(PM10mean,3))
        return {
                "tags":{
                    "sensor": "SDS011"},
                "fields":{
                    "PM2.5":round(PM25mean,2),
                    "PM10":round(PM10mean,2)}
                    },test_var
		


######################################################################################
######################################################################################
#Fonction pour extraire le numéro du Raspberry pour envoyer avec les données
def getSerial():
    with open('/proc/cpuinfo','r') as f:
        for line in f:
            if line[0:6]=='Serial':
                return(line[10:26])
    f.close()
    raise Exception('CPU serial not found')

raspId = getSerial()


######################################################################################
######################################################################################
#Fonction pour integrer les donnees dans notre base INFLUX DB
infl = int(1)
measurement = 'airquality_measurement'
client = InfluxDBClient(host = 'dmz-aircasting',
                        port = '8086',
                      username = 'root',
                     password = 'root',
                    database = 'test')
#Pour info format de base test : time;Id_rasp;PM10;PM2.5;capteur;port;sensor;site
######################################################################################  




#lancement du code
if __name__ == "__main__":
  
  s = SDS011()
  fichier=open(nom_fichier,"a") 
  try:
    while True:
        res,test_var= s.moyenne(moyenne)
        #print(res)
        #print(test_var)
        res["tags"]["Id_rasp"]= raspId
        res["tags"]["site"] = site
        res["tags"]["capteur"]=num_serie_capteur
        res["tags"]["sensor"] = sensor
        res["measurement"] = measurement
        if infl == 1: client.write_points([res])
        fichier.write("%s;%s;%s;%s;%s\n" %(test_var,site,raspId,num_serie_capteur,sensor))
  except KeyboardInterrupt: 
        fichier.close()