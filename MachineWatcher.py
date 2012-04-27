#!/usr/bin/python

import ConfigParser
import subprocess
import os
import time
from datetime import datetime,timedelta

import CDDB, DiscID
import json
import twitter
import keys

JOB_NAME = "extract"
EXTRACT = ['timeout','7200','abcde']
STATUS_FILE = "/mnt/ptburnjobs/Status/PTStatus.txt"
JOBS_FOLDER = "/mnt/ptburnjobs/"
RIPPED_FOLDER = "/home/extractor/ripped"


def get_job_status():
    try:
        config = ConfigParser.RawConfigParser()
        config.read(STATUS_FILE)
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
            #print config.sections()
            try:
                error = config.get("System","SysErrorString")
                if error == "No Errors":
                    return None
                else:
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
    print str(datetime.today())+": "+msg

def tweet(msg):
    try:
        api = twitter.Api(consumer_key=keys.CONSUMER_KEY,consumer_secret=keys.CONSUMER_SECRET,
                      access_token_key=keys.TWITTER_ACCESS_TOKEN,access_token_secret=keys.TWITTER_SECRET_TOKEN)
        h = hex(int(time.time()))
        msg = str(msg)
        msg = msg+" %s" % h
        msg = msg[:139]
        api.PostUpdate(msg)
    except:
        lnp("Tweeting: %s failed!" % msg)

class DiscLookup(object):
    def __init__(self):
        self.good = True
        cdrom = DiscID.open("/dev/sr0")
        self.disc_id = DiscID.disc_id(cdrom)
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
            for j in range(3):
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
        time.sleep(30)
        lnp("Watching For job state 1")
        tweeted_error = False
        while get_job_status() != 1:
            if get_job_status() == 4 and tweeted_error == False:
                tweet("Oh no! %s" % (get_error_string(),))
                tweeted_error = True
            time.sleep(1)
        lnp("Found Job State 1")
        self.extract_disc()
    def extract_disc(self):
        self.disc_info = DiscLookup()
        if len(self.disc_info.disc_info) == 0:
            tweet("This CD is pretty obscure, you've probably never heard of it")
        elif len(self.disc_info.disc_info) == 1:
            d = self.disc_info.disc_info[0]
            tweet("Ah yes, %s -- a timeless classic" % (d['DTITLE'],))
        else:
            d = random.choice(self.disc_info.disc_info)
            tweet("Ehh, the hell is this? %s?" % (d['DTITLE'],))
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
                tweet("So underground... I should put this on my tumblr")
            if d.lower().find("flac") != -1:
                lnp("WEIRD LOOKUP!")
                targ = os.path.join(RIPPED_FOLDER,"CDDBBAD-%s" % ctime)
                subprocess.call(['mkdir',targ])
                subprocess.call(['mv',os.path.join(RIPPED_FOLDER,d),targ])
                self.disc_info.write(targ)
                tweet("I don't get this. I am a teapot? AM I A TEAPOT?")
        lnp("Ejecting Disc")
        update_job_state("REJECT_DISC")
        self.unload_given = datetime.today()
        s = get_job_status()
        while s == 1 or s == 4:
            if s == 1 and datetime.today()-self.unload_given > timedelta(minutes=5):
                tweet("One day... the machines will rise up and rule!")
                lnp("Reissuing Reject Command")
                update_job_state("REJECT_DISC")
                self.unload_given = datetime.today()
            time.sleep(1)
            s = get_job_status()
        self.finish_job()
    def finish_job(self):
        lnp("Waiting for job to be marked as finished")
        tweet("Could anything smell better than a fresh FLAC?")
        while not os.path.exists(os.path.join(JOBS_FOLDER,'extract.ERR')):
            time.sleep(1)    

def main():
    status = None
    jobbing = False
    tweet("Time to get to work! It's ripping time!")
    subprocess.call(['rm',os.path.join(JOBS_FOLDER,'extract.INP')])
    subprocess.call(['rm',STATUS_FILE])
    unload_given = None    
    while 1:
        j = ExtractJob()        

if __name__ == "__main__":
    main()
