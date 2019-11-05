from __future__ import print_function
import serial
import time
import struct
import datetime
import sys
import os.path
import numpy as np
import configparser  #Module pour gérer l import d un fichier de configuration
import argparse #Module pour ajouter des paramètres lors de l appel du script 
from influxdb import InfluxDBClient  #Module pour gérer l export des données vers la base InfluxDB
import os
sensor='OPC'


#############################################
#############################################
#INFO A REMPLIR AVANT LANCEMENT DU FICHIER

port = '/dev/ttyUSB0'
WD = '/home/pi/Documents/Intercomp/log'
nom_fichier = WD+'opc.txt'
moyenne=10
num_serie_capteur = '123154'
site='Grenoble les frene'

###########################################
#############################################



class opc:

#Fonction d'initialisation 
    def __init__(self):
        serial_opts = {
        # built-in serial port is "COM1"
        # USB serial port is "COM4"
        "port": "/dev/ttyACM0",
        "baudrate": 9600,
        "parity": serial.PARITY_NONE,
        "bytesize": serial.EIGHTBITS,
        "stopbits": serial.STOPBITS_ONE,
        "xonxoff": False,
        "timeout": 1
        }
        #ofile=sys.argv[1]
        self.ser = serial.Serial(**serial_opts)
        if self.ser.isOpen():
            self.ser.close()
        self.ser.open()
        print("Init")
        time.sleep(1)
        self.ser.write(bytearray([0x5A,0x01]))
        nl = self.ser.read(3)
        #print(nl)
        time.sleep(.1)
        self.ser.write(bytearray([0x5A,0x03]))
        nl=self.ser.read(9)
        #print(nl)
        time.sleep(.1)
        self.ser.write(bytearray([0x5A,0x02,0x92,0x07]))
        nl=self.ser.read(2)
        #print(nl)
        time.sleep(.1)

# Turn fan and laser off
    def fanOff(self):
        self.ser.write(bytearray([0x61,0x03]))
        nl = self.ser.read(2)
        #print(nl)
        time.sleep(.1)
        self.ser.write(bytearray([0x61,0x01]))
        nl = self.ser.read(2)
        #print(nl)
        time.sleep(.1)

# Turn fan and laser on
    def fanOn(self):
        self.ser.write(bytearray([0x61,0x03]))
        nl = self.ser.read(2)
        #print(nl)
        time.sleep(.1)
        self.ser.write(bytearray([0x61,0x00]))
        nl = self.ser.read(2)
        #print(nl)
        time.sleep(.1)

    def combine_bytes(self,LSB, MSB):
        return (MSB << 8) | LSB

#Fonction pour acquerir les donnees  
    def getHist(self,f):
        self.ser.write(bytearray([0x61,0x30]))
        nl=self.ser.read(2)
        #print(nl)
        time.sleep(.1)
        br = bytearray([0x61])
        for i in range(0,62):
            br.append(0x30)
            
        self.ser.write(br)
        ans=bytearray(self.ser.read(1))
        ans=bytearray(self.ser.read(62))
        
        data={}
        data['Bin 0'] = self.combine_bytes(ans[0],ans[1])
        data['Bin 1'] = self.combine_bytes(ans[2],ans[3])
        data['Bin 2'] = self.combine_bytes(ans[4],ans[5])
        data['Bin 3'] = self.combine_bytes(ans[6],ans[7])
        data['Bin 4'] = self.combine_bytes(ans[8],ans[9])
        data['Bin 5'] = self.combine_bytes(ans[10],ans[11])
        data['Bin 6'] = self.combine_bytes(ans[12],ans[13])
        data['Bin 7'] = self.combine_bytes(ans[14],ans[15])
        data['Bin 8'] = self.combine_bytes(ans[16],ans[17])
        data['Bin 9'] = self.combine_bytes(ans[18],ans[19])
        data['Bin 10'] = self.combine_bytes(ans[20],ans[21])
        data['Bin 11'] = self.combine_bytes(ans[22],ans[23])
        data['Bin 12'] = self.combine_bytes(ans[24],ans[25])
        data['Bin 13'] = self.combine_bytes(ans[26],ans[27])
        data['Bin 14'] = self.combine_bytes(ans[28],ans[29])
        data['Bin 15'] = self.combine_bytes(ans[30],ans[30])
        data['period'] = struct.unpack('f',bytes(ans[44:48]))[0]
        data['pm1'] = struct.unpack('f',bytes(ans[50:54]))[0]
        data['pm2'] = struct.unpack('f',bytes(ans[54:58]))[0]
        data['pm10'] = struct.unpack('f',bytes(ans[58:]))[0]
        return(data)
  
#Fonction pour le calcul de la moyenne    
    def moyenne(self,sample,f):
        i=0
        PM25list = list()
        PM10list = list()
        while i<=sample:
            t=self.getHist(f)
            ts = time.time()
            tnow = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
            data=t
            print(data['pm2'],data['pm10'])
            if (data['pm2']) !='': PM25list.append(data['pm2'])
            if (data['pm10']) !='': PM10list.append(data['pm10'])
            i+=1
            time.sleep(1)
        #print (PM25list,PM10list)
        PM25res = np.array(PM25list)
        PM25mean = PM25res.mean()  #Moyenne PM25
        PM10res = np.array(PM10list)
        PM10mean = PM10res.mean()  #Moyenne PM10
        test_var=tnow+";"+"PM2.5 ;"+str(round(PM25mean,3))+";PM10;"+str(round(PM10mean,3))
        return {
             "tags":{
                    "sensor": sensor},
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



######################################################################################
######################################################################################
#Fonction pour integrer les donnees dans notre base INFLUX DB
infl = int(0)
measurement = 'airquality_measurement'
client = InfluxDBClient(host = 'dmz-aircasting',
                        port = '8086',
                      username = '****',
                     password = '****',
                    database = 'test')
#Pour info format de base test : time;Id_rasp;PM10;PM2.5;capteur;port;sensor;site
######################################################################################

#CORPS DU PROGRAMME
 
if __name__ == "__main__":
        
     o=opc()
     raspId = getSerial()  
     print("Fan on")
     o.fanOn()
     time.sleep(10)
     fichier=open(nom_fichier,"a") 
     #fichier.write("time;b0:0.38-0.54;b1:0.54;b2:0.78;b3:1;b4:1.3;b5:1.6;b6:2.1;b7:3;b8:4;b9:5;b10:6.5;b11:8;b12:10;b13:12;b14:14;b15:>16;period;pm1;pm2;pm10 \n")
     try:
         while True:
             res,test_var= o.moyenne(moyenne,fichier)
             #print(test_var)
             res["tags"]["Id_rasp"]= raspId
             res["tags"]["site"] = site
             res["tags"]["capteur"]=num_serie_capteur
             res["tags"]["sensor"] = sensor
             res["measurement"] = measurement
             #print(data)
             if infl == 1: client.write_points([res])
             fichier.write("%s;%s;%s;%s;%s\n" %(test_var,site,raspId,num_serie_capteur,sensor))            
             #fichier.write( tnow + ";" + str(data['Bin 0']) + ";"  + str(data['Bin 1']) + ";"  + str(data['Bin 2']) + ";"  + str(data['Bin 3']) + ";"  + str(data['Bin 4']) + ";"  + str(data['Bin 5']) + ";"  + str(data['Bin 6']) + ";"  + str(data['Bin 7']) + ";"  + str(data['Bin 8']) + ";"  + str(data['Bin 9']) + ";"  + str(data['Bin 10']) + ";"  + str(data['Bin 11']) + ";"  + str(data['Bin 12']) + ";"  + str(data['Bin 13']) + ";"  + str(data['Bin 14']) + ";"  + str(data['Bin 15']) + ";"  + str(data['period']) + ";"  + str(data['pm1']) + ";"  + str(data['pm2']) + ";"  + str(data['pm10'])+"\n") 
             #time.sleep(59)
     except KeyboardInterrupt: 
       fichier.close()            
     
        
    
