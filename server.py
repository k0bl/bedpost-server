#!/usr/bin/env python
# coding: utf-8

"""
This is a dynamic http server for saving configutations. At the 
moment, I will keep the configuration (admin) backend portion 
separate from the main view application.
"""
import json
import requests
import pyjsonrpc
import sqlite3
import subprocess
import threading
#Globals
database = 'bedposttest.db'
# conn = sqlite3.connect('pyjsonrpctest2.db')
# c = conn.cursor()


# #try to insert values into 
# c.execute("INSERT INTO locations VALUES ('longbeach', '90806', 'lgb')")

def resetDatabase():
        conn = sqlite3.connect(database)
        c = conn.cursor()
        #Drop the tables if they already exist

        c.execute("DROP TABLE IF EXISTS transfers")
      
        c.execute('''CREATE TABLE transfers
            (transfer_id INTEGER PRIMARY KEY ASC, bed_number text, clinicore_id text, location text, study_folder text, status text)''')

class RequestHandler(pyjsonrpc.HttpRequestHandler):
    

    @pyjsonrpc.rpcmethod
    def startTransfer(self, bedNumber, clinicoreId, location):
        conn = sqlite3.connect(database)
        c = conn.cursor()
        print bedNumber
        print clinicoreId
        print location
        
        dbBedNumber = str(bedNumber)
        dbClinicoreId = str(clinicoreId)
        dbLocation = str(location)
        dbStudyFolder = str("Please wait.....")
        dbStatus = str("Uploading to Server")
        c.execute ("INSERT INTO transfers VALUES (null, ?, ?, ?, ?, ?);", (dbBedNumber, dbClinicoreId, dbLocation, dbStudyFolder, dbStatus))        
        
        print "CPC Insertion is done"
        conn.commit()

        last_id = c.lastrowid
        
        #start rsync file transfer here


        print "Last ID is set to last inserted row"
        print last_id

        print "Printing selection"
        print c.execute("SELECT * FROM transfers WHERE transfer_id = ?", (last_id,))
        row = c.fetchone()

        conn.close()
        print row

        print "Now copying from tech pc"
        
        copy_thread = threading.Thread(target=self.startCopy, args=(dbClinicoreId, dbLocation, dbBedNumber))
        copy_thread.start()
        print "Copy thread created"
    
    #copy study from tech pc
    def startCopy(self, cid, loc, bed):
        self.copyFromTechPc(cid, loc, bed)

    def copyFromTechPc(self, cid, loc, bed):    
        #set cmd variable

        cmd = "rsync -azv --ignore-existing cody@bed"+bed+"."+loc+".local:/cygdrive/c/Data/ /srv/bedpost/"+loc+"/"+bed+"/"
        
        print "Starting Copy from Tech PC"

        #subprocess for copy from PC
        proc = subprocess.Popen(cmd, shell=True,
            stdout = subprocess.PIPE,
            stderr = subprocess.PIPE)
        streamdata = proc.communicate()[0]

        print "Done copying data from collection PC"
        
        self.updateFolderName(cid, loc, bed)

    #subprocess for directory listing, tail last line
    def updateFolderName(self, cid, loc, bed):
        lscmd = "ls -rt /srv/bedpost/"+loc+"/"+bed+"/ | tail -1"

        lsproc = subprocess.Popen([lscmd], stdout=subprocess.PIPE, shell=True)
        (out, err)=lsproc.communicate()
        output = out

        conn = sqlite3.connect(database)
        c = conn.cursor()

        dbClinicoreId = cid
        dbFolderName = str(output)

        print "dbFolderName: ", dbFolderName

        c.execute ("UPDATE transfers SET study_folder=? WHERE clinicore_id=?", (dbFolderName, dbClinicoreId))

        print "Folder Name update is done."
        conn.commit()

        conn.close()

        copyDone = "On Server"
        self.updateDownloadStatus(dbClinicoreId, copyDone)

        print "Update Download Status is done"

    @pyjsonrpc.rpcmethod
    def updateDownloadStatus(self, cid, status):
        conn = sqlite3.connect(database)
        c = conn.cursor()
        
        dbClinicoreId = str(cid)
        dbStatus = str(status)

        c.execute ("UPDATE transfers SET status=? WHERE clinicore_id=?", (dbStatus, dbClinicoreId))

        print "Download Status update is done."
        conn.commit()

        conn.close()

    @pyjsonrpc.rpcmethod
    def returntransfers(self):
        conn = sqlite3.connect(database)
        c = conn.cursor()
        c.execute('SELECT * FROM transfers')
        results = c.fetchall()
        
        print "printing transfers"
        print '\nindividual records'
        
        for result in results:
            print result
        return results

http_server = pyjsonrpc.ThreadingHttpServer(
    
    server_address = ('10.0.3.112', 5050),
    #server_address = ('192.168.1.7', 5050),
    RequestHandlerClass = RequestHandler
)
print "resetting database"
resetDatabase()

print "Starting HTTP server ..."
print "URL: http://10.0.3.112:5050"
#print "URL: 192.168.1.7:5050"

try:
    http_server.serve_forever()
except KeyboardInterrupt:
        http_server.shutdown()
print "Stopping HTTP Server"

