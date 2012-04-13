#!/usr/bin/python

import ConfigParser
import subprocess
import os
import time
from datetime import datetime,timedelta

JOB_NAME = "extract"
EXTRACT = ['timeout','7200','abcde']
STATUS_FILE = "/mnt/ptburnjobs/Status/PTStatus.txt"
JOBS_FOLDER = "/mnt/ptburnjobs/"
RIPPED_FOLDER = "/home/kmnr-extractor/ripped"

def get_job_status():
    try:
        config = ConfigParser.RawConfigParser()
        config.read(STATUS_FILE)
        print config.sections()
        try:
            status = config.getint(JOB_NAME,'LoadDiscState0')
        except ConfigParser.NoOptionError:
            return -1
        except ConfigParser.NoSectionError:
            return 0
        return status
    except:
        print "IO Error, give me a bit"
        time.sleep(2)
        return 0
    
def update_job_state(state):
    path = os.path.join(JOBS_FOLDER,"%s.%s" % (JOB_NAME,"ptm"))
    print "Writing to %s" % path
    f = open(path,'w')
    f.write("Message= %s\n" % state)
    f.write("DiscID=0\n")
    f.close()
   
def lnp(msg):
    f = open('ripper.log','a')
    f.write(str(datetime.today())+": "+msg+"\n")
    f.close()
    print msg

def main():
    status = None
    jobbing = False
    subprocess.call(['rm',os.path.join(JOBS_FOLDER,'extract.INP')])
    subprocess.call(['rm',STATUS_FILE])
    unload_given = None    
    while 1:
        if jobbing == False:
            lnp("Requesting Job")
            subprocess.call(['rm',os.path.join(JOBS_FOLDER,'extract.ERR')])
            subprocess.call(['cp','extract.jrq',JOBS_FOLDER])
            jobbing = True
            lnp("Registered Job")
            time.sleep(60)
            lnp("Watching For job state 1")
        elif get_job_status() == 1 and status != "PROCESSING":
            lnp("Found Job State 1")
            if subprocess.call(EXTRACT) != 0:
                f = open('FAILED-%s.dat' % int(time.time()),'w')
                subprocess.call(['cd-discid'],stdout=f)
                f.close()
            dirs = os.listdir(RIPPED_FOLDER)
            ctime = int(time.time()) 
            for d in dirs:
                if d.lower().find("unknown") != -1:
                    lnp("CDDB Missing!")
                    targ = os.path.join(RIPPED_FOLDER,"CDDBBAD-%s" % ctime)
                    subprocess.call(['mv',os.path.join(RIPPED_FOLDER,d),targ])
                    f = open(os.path.join(targ,'CDDB.dat'),'w')
                    subprocess.call(['cd-discid'],stdout=f)
                    f.close()
                if d.lower().find("flac") != -1:
                    lnp("WEIRD LOOKUP!")
                    targ = os.path.join(RIPPED_FOLDER,"CDDBBAD-%s" % ctime)
                    subprocess.call(['mkdir',targ])
                    subprocess.call(['mv',os.path.join(RIPPED_FOLDER,d),targ])
                    f = open(os.path.join(targ,'CDDB.dat'),'w')
                    subprocess.call(['cd-discid'],stdout=f)
                    f.close()
            lnp("Waiting for accept!")
            update_job_state("PROCESS_DISC")
            status = "PROCESSING"
            unload_given = datetime.today()
        elif get_job_status() == 1 and status == "PROCESSING":
            if datetime.today()-unload_given > timedelta(minutes=10):
                #Apparently sometimes these commands can fail!?
                lnp("Failed to move on after reading disc")
                unload_given = datetime.today()
                update_job_state("PROCESS_DISC")
        elif get_job_status() == 3 and status == "PROCESSING":
            lnp("Ready to accept")
            # For some reason the command they gave to accept rejects the disc,
            # But that seems to be okay, because it makes it so the job is 
            # repeatable more easily
            update_job_state("REJECT_DISC")
            unload_given = datetime.today()
            status = None
        elif get_job_status() == 3 and status == None and jobbing == True:
            if datetime.today()-unload_given > timedelta(minutes=10):
                lnp("Failed to accept unload command")
                update_job_state("REJECT_DISC")
                unload_given = datetime.today()
        elif os.path.exists(os.path.join(JOBS_FOLDER,'extract.ERR')):
            lnp("Disc Job Finished")
            jobbing = False
            time.sleep(2)
        print "Job Status: %s Local Status %s Jobbing %s" % (get_job_status(),status,jobbing)
        time.sleep(2)
        
if __name__ == "__main__":
    main()
