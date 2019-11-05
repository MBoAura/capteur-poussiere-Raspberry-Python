import serial
from datetime import datetime
import time
import numpy as np
import configparser  #Module pour gérer l import d un fichier de configuration
import argparse #Module pour ajouter des paramètres lors de l appel du script 
from influxdb import InfluxDBClient  #Module pour gérer l export des données vers la base InfluxDB
import os
sensor='PMS7003'

#############################################
#INFO A REMPLIR AVANT LANCEMENT DU FICHIER

port = '/dev/ttyUSB0'
nom_fichier = 'PMS7003.txt'
moyenne=10
num_serie_capteur = 'blabla'
site='Grenoble les frene'


###########################################


MSG_CHAR_1 = b'\x42' # First character to be recieved in a valid packet
MSG_CHAR_2 = b'\x00' # Second character to be recieved in a valid packet
nByte = 31

class PMS7003:
    "Objet PMS7003"
    

    def acquisition(self):
      capteur = serial.Serial(port,baudrate = 9600,timeout=1)
      byte1 = capteur.read(size = 1)
      print("byte 1: ",byte1)
      if byte1 == MSG_CHAR_1:
        datas = capteur.read(size = 39)
        PM25=datas[12]+datas[13]
        PM10=datas[14]+datas[15]
        print(PM25)
        #print(datas)
        #print('\n======= PMS5003ST ========\n'
#              'PM1.0(CF=1): {}\n'
#              'PM2.5(CF=1): {}\n'
#              'PM10 (CF=1): {}\n'
#              'PM1.0 (STD): {}\n'
#              'PM2.5 (STD): {}\n'
#              'PM10  (STD): {}\n'
#              '>0.3um     : {}\n'
#              '>0.5um     : {}\n'
#              '>1.0um     : {}\n'
#              '>2.5um     : {}\n'
#              '>5.0um     : {}\n'
#              '>10um      : {}\n'
#              'HCHO       : {}\n'
#              'temperature: {}\n'
#              'humidity(%): {}'.format(datas[4]+datas[5],
#                                       datas[6]+datas[7],
#                                       datas[8]+datas[9],
#                                       datas[10]+datas[11], #PM1
#                                       datas[12]+datas[13],
#                                       datas[14]+datas[15],
#                                       datas[16]+datas[17],
#                                       datas[18]+datas[19],
#                                       datas[20]+datas[21],
#                                       datas[22]+datas[23],
#                                       datas[24]+datas[25],
#                                       datas[26]+datas[27],
#                                       (datas[28]+datas[29])/1000.0,
#                                       (datas[30]+datas[31])/10.0,
#                                       (datas[32]+datas[33])/10.0))
        return {
                "tags":{
                    "sensor": "PMS"},
                "fields":{
                    "PM25":PM25,
                    "PM10":PM10}
                    }
      else:
            print("En attente de données valides ")
            return {"tags":{
                    "sensor": "SDS011"},
                "fields":{
                    "PM25":'',
                    "PM10":''}
                    }         
                    
                    
    def moyenne(self,sample):
        i=0
        print(i)
        PM25list = list()
        PM10list = list()
        while i<=sample:
            res=self.acquisition()
            ts = time.time()
            #datas=t
            if res["fields"]["PM25"]!='': PM25list.append(res["fields"]["PM25"])
            if res["fields"]["PM10"] !='': PM10list.append(res["fields"]["PM10"])
            i+=1
            time.sleep(1)
        #print (PM25list,PM10list)
        PM25res = np.array(PM25list)
        PM25mean = PM25res.mean()  #Moyenne PM25
        PM10res = np.array(PM10list)
        PM10mean = PM10res.mean()  #Moyenne PM10
        test_var="{}; PM2.5; {} ; PM10; {}".format(datetime.now().strftime("%Y/%m/%d %H:%M:%S"),round(PM25mean,3),round(PM10mean,3))
        return {
             "tags":{
                    "sensor": sensor},
                "fields":{
                    "PM2.5":round(PM25mean,2),
                    "PM10":round(PM10mean,2)}
                    },test_var
    
    
######################################################################################
# extracts serial from cpuinfo ################################
#Extraire le numero du Raspberry pour envoyer avec les donnees
def getSerial():
    """Fonction pour récupérer le numéro de série du raspberry"""
    with open('/proc/cpuinfo','r') as f:
        for line in f:
            if line[0:6]=='Serial':
                return(line[10:26])
    f.close()
    raise Exception('CPU serial not found')

raspId = getSerial()


##########################################
##########################################
# Gestion InfluxDB ###################################################################
infl = int(1)
measurement = 'airquality_measurement'
client = InfluxDBClient(host = 'dmz-aircasting',
                        port = '8086',
                      username = '****',
                     password = '****',
                    database = 'test')
#format de base : time;Id_rasp;PM10;PM2.5;capteur;port;sensor;site

######################################################################################


#lancement du code
if __name__ == "__main__":
  
  s = PMS7003()
  fichier=open(nom_fichier,"a") 
  print("ok")
  try:
    while True:
        res,test_var= s.moyenne(moyenne)
        print(res)
        print(test_var)
        res["tags"]["Id_rasp"]= raspId
        res["tags"]["site"] = site
        res["sensor"] = num_serie_capteur
        res["measurement"] = measurement
        if infl == 1: client.write_points([res])
        fichier.write("%s;%s;%s;%s;%s\n" %(test_var,site,raspId,num_serie_capteur,sensor))
  except KeyboardInterrupt: 
        fichier.close()    
