import serial
from datetime import datetime
import time
import argparse #Module pour ajouter des paramÃ¨tres lors de l appel du script 
from influxdb import InfluxDBClient  #Module pour gÃ©rer l export des donnÃ©es vers la base InfluxDB
import os
sensor='NextPM'


#############################################
#INFO A REMPLIR AVANT LANCEMENT DU FICHIER

port = '/dev/ttyUSB0'
nom_fichier = 'nextpm.txt'
moyenne=10
num_serie_capteur = '123154'
site='Grenoble les frene'
###########################################
#############################################





class NextPM:
    
#Fonction d'initialisation      
    def __init__(self,port=port,baudrate = 115200,timeout = 1):
        self.serial = serial.Serial(port = port,
                                 baudrate = baudrate,
                                 bytesize=serial.EIGHTBITS,
                                 parity=serial.PARITY_EVEN,
                                 stopbits=serial.STOPBITS_ONE,
                                 timeout = 1)
 
 
#Fonction de parametrage du capteur        
    def parametrage(self,moyenne):
        print("Parametrage du capteur: ")
        if int(moyenne) == 1: self.serial.write(b'\x81\x11\x6E') #1s
        if int(moyenne) == 10: self.serial.write(b'\x81\x12\x6D') #10s
        if int(moyenne) == 60: self.serial.write(b'\x81\x13\x6C') #60s
        else: print("Attention: changer la moyenne dans fichier de config.ini")
        time.sleep(0.36)
        response = self.serial.read(15)
        print("Reponse paramÃ©trage: ",response)
        print("Parametrage nextPM: OK")
        time.sleep(1.1)


#Fonction pour acquerir les données moyennées    
    def moyenne(self,moyenne):
        #Fonction pour lire les donnÃ©es du capteur
        if int(moyenne)  == 1: self.serial.write(b'\x81\x11\x6E') #1s
        if moyenne == 10: self.serial.write(b'\x81\x12\x6D') #10s
        if moyenne == 60: self.serial.write(b'\x81\x13\x6C') #60s
        time.sleep(moyenne)
        byte = self.serial.read(size = 1)
        if byte == b'\x81':
            sentence = self.serial.read(size=15)
            pm_1 = (sentence[9]+sentence[10])/10 #PM1 en microg par m3
            pm_25 = (sentence[11]+sentence[12])/10 #PM2.5 en microg par m3
            pm_10 = (sentence[13]+sentence[14])/10 #PM10 en microg par m3
            line = "PM1: {} Âµg/m3, PM2.5: {} Î¼g/m3, PM10: {} Î¼g/m3".format(pm_1,pm_25, pm_10)
            test_var = "{}; PM2.5; {} ; PM10; {}".format(datetime.now().strftime("%Y/%m/%d %H:%M:%S"),round(pm_25,3),round(pm_10,3))
            #print(test_var)
            #print(datetime.datetime.now().strftime("%d %b %Y %H:%M:%S : "),line)
            return {
                "tags":{
                    "sensor": "Next PM"},
                "fields":{
                    "PM2.5":round(pm_25,2),
                    "PM10":round(pm_10,2)}
                    },test_var
            
        else:
            print("Pas de donnÃ©es valides")
            PM1 =''
            PM25 = ''
            PM10 = ''
            return {
                "tags":{
                    "sensor": "Next PM"},
                "fields":{
                    "PM2.5":round(pm_25,2),
                    "PM10":round(pm_10,2)}
                    }

            
######################################################################################
######################################################################################
#Fonction pour extraire le numÃ©ro du Raspberry pour envoyer avec les donnÃ©es
def getSerial():
    with open('/proc/cpuinfo','r') as f:
        for line in f:
            if line[0:6]=='Serial':
                return(line[10:26])
    f.close()
    raise Exception('CPU serial not found')




######################################################################################
######################################################################################
#Fonction pour integrer les données dans notre base INFLUX DB
infl = int(1)
measurement = 'airquality_measurement'
client = InfluxDBClient(host = 'dmz-aircasting',
                        port = '8086',
                      username = '****',
                     password = '****',
                    database = 'test')
#Pour info format de base test : time;Id_rasp;PM10;PM2.5;capteur;port;sensor;site
######################################################################################    



#lancement du code
if __name__ == "__main__":
  
  s = NextPM()
  raspId = getSerial()
  print(raspId)
  fichier=open(nom_fichier,"a") 
  try:
    while True:
        res,data= s.moyenne(moyenne)
        print(res)
        #print(test_var)
        res["tags"]["Id_rasp"]= raspId
        res["tags"]["site"] = site
        res["tags"]["capteur"]=num_serie_capteur
        res["tags"]["sensor"] = sensor
        res["measurement"] = measurement
        if infl == 1: client.write_points([res])
        fichier.write("%s;%s;%s;%s;%s\n" %(data,site,raspId,num_serie_capteur,sensor))
  except KeyboardInterrupt: 
        fichier.close()
