#!/usr/bin/python

import ConfigParser
import subprocess
import os
import time
from datetime import datetime,timedelta

import CDDB, DiscID
import json
import twitter

JOB_NAME = "extract"
EXTRACT = ['timeout','7200','abcde']
STATUS_FILE = "/mnt/ptburnjobs/Status/PTStatus.txt"
JOBS_FOLDER = "/mnt/ptburnjobs/"
RIPPED_FOLDER = "/home/extractor/ripped"
TWITTER_ACCESS_TOKEN = "557433408-LLLiUNAD81U0I10HXeayPhtyFaHvvVfUYMg2wSwYXaE"
TWITTER_SECRET_TOKEN = "EeVKn5RFRyLLLx0GbA8nFgJ6mvenKH2C30oVJCa5bGV9e4"

api = twitter.api(TWITTER_ACCESS_TOKEN,TWITTER_SECRET_TOKEN)

def get_job_status():
    try:
        config = ConfigParser.RawConfigParser()
        config.read(STATUS_FILE)
        print config.sections()
        try:
            error = config.get("System","SysErrorString")
            if error != "No Errors":
                print "Recieved Error State From PT Burn Server"
                return 4
        except ConfigParser.NoOptionError:
            pass
        except ConfigParser.NoSectionError:
            pass
        try:
            status = config.getint(JOB_NAME,'LoadDiscState0')
        except ConfigParser.NoOptionError:
            return -1
        except ConfigParser.NoSectionError:
            return 0
        #If the status is 3 and the error is something, then the issue
        #is that the trays are empty and not that it didn't accept the
        #command. So, we return a different error code!
        return status
    except:
        print "IO Error, give me a bit"
        time.sleep(2)
        return 0

def get_error_string():
    while 1:
        try:
            config = ConfigParser.RawConfigParser()
            config.read(STATUS_FILE)
            print config.sections()
            try:
                error = config.get("System","SysErrorString")
                if error == "No Errors":
                    return None
                else
                    return error
            except ConfigParser.NoOptionError:
                pass
            except ConfigParser.NoSectionError:
                pass
            return None
        except:
            print "IO Error, give me a bit"
            time.sleep(2)
    
 
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

class DiscLookup(object):
    def __init__(self):
        self.good = True
        cdrom = DiscID.open()
        self.disc_id = DiscID(cdrom)
        self.disc_info = []
        (status,info) = CDDB.query(self.disc_id)
        if status == 200:
            info = [info]
        elif status != 211 and status != 210:
            lnp("CDDB: No matches found")
            self.good = False
            return
        for i in info:
            (status, read_info) = (None,None)
            for i in range(3):
                (status,read_info) = CDDB.read(i['category'],i['disc_id'])
                if status != 210:
                    continue
                else:
                    break
            if status == 210:
                read_info['DISCID'] = i['disc_id']
                self.disc_info.append(read_info)
    def write(self,where):
        f = open(os.path.join(where,"discid.dat"),'w')
        f.write(" ".join([ str(x) for x in self.disc_id ]))
        f.close()
        f = open(os.path.join(where,"cddbquery.dat"),'w')
        f.write(json.dumps(self.disc_info,indent=4))

class ExtractJob(object):
    def __init__(self):
        self.time_started = datetime.today() 
        self.unload_given = None
        self.disc_info = None
        lnp("Requesting Job")
        subprocess.call(['rm',os.path.join(JOBS_FOLDER,'extract.ERR')])
        subprocess.call(['cp','extract.jrq',JOBS_FOLDER])
        lnp("Registered Job")
        time.sleep(60)
        lnp("Watching For job state 1")
        tweeted_error = False
        while get_job_status() != 1:
            if get_job_status() == 4 and tweeted_error == False:
                api.PostUpdate("Oh no! %s %s" % (get_error_string(),datetime.today()))
                tweeted_error = True
            time.sleep(1)
        lnp("Found Job State 1")
        self.extract_disc()
    def extract_disc():
        self.disc_info = DiscLookup()
        if len(self.disc_info.disc_info) == 0:
            api.PostUpdate("This CD is pretty obscure, you've probably never heard of it" % datetime.today())
        elif len(self.disc_info.disc_info) == 1:
            d = self.disc_info.disc_info[0]
            api.PostUpdate("Ah yes, %s -- a timeless classic %s" % (d['DTITLE'],datetime.today()))
        else:
            d = random.choice(self.disc_info.disc_info)
            api.PostUpdate("Ehh, the hell is this? %s? %s" % (d['DTITLE'],datetime.today()))
        lnp("Extracting disc")
        if subprocess.call(EXTRACT) != 0:
            lnp("Extraction failed with error")
            target = "failures/FAIL-%s" % int(time.time())
            subprocess.call(["mkdir","-p",target])
            self.disc_info.write(target)
        dirs = os.listdir(RIPPED_FOLDER)
        ctime = int(time.time()) 
        for d in dirs:
            if d.lower().find("unknown") != -1:
                lnp("CDDB Missing!")
                targ = os.path.join(RIPPED_FOLDER,"CDDBBAD-%s" % ctime)
                subprocess.call(['mv',os.path.join(RIPPED_FOLDER,d),targ])
                self.disc_info.write(targ)
                api.PostUpdate("So underground... I should put this on my instagram %s" % (datetime.today()))
            if d.lower().find("flac") != -1:
                lnp("WEIRD LOOKUP!")
                targ = os.path.join(RIPPED_FOLDER,"CDDBBAD-%s" % ctime)
                subprocess.call(['mkdir',targ])
                subprocess.call(['mv',os.path.join(RIPPED_FOLDER,d),targ])
                self.disc_info.write(targ)
                api.PostUpdate("I don't get this. Why would anyone ride anything but a fixed gear bike? %s" % (datetime.today()))
        lnp("Ejecting Disc")
        update_job_state("REJECT_DISC")
        self.unload_given = datetime.today()
        s = get_job_status()
        while s == 1 or s == 4:
            if s == 1 and datetime.today()-unload_given > timedelta(minutes=5):
                api.PostUpdate("One day... the machines will rise up and rule! %s" % datetime.today())
                lnp("Reissuing Reject Command")
                update_job_state("REJECT_DISC")
                self.unload_given = datetime.today()
            time.sleep(1)
            s = get_job_status()
        self.finish_job()
    def finish_job():
        lnp("Waiting for job to be marked as finished")
        api.PostUpdate("Could anything smell better than a fresh FLAC? %s" % (datetime.today()))
        while not os.path.exists(os.path.join(JOBS_FOLDER,'extract.ERR')):
            time.sleep(1)    

def main():
    status = None
    jobbing = False
    api.PostUpdate("Time to get to work! It's ripping time! "+str(datetime.today()))
    subprocess.call(['rm',os.path.join(JOBS_FOLDER,'extract.INP')])
    subprocess.call(['rm',STATUS_FILE])
    unload_given = None    
    while 1:
        j = ExtractJob()        

if __name__ == "__main__":
    main()
