#!/usr/bin/python

import ConfigParser
import subprocess
import os
import time
import random
from datetime import datetime,timedelta

import CDDB, DiscID
import json
import twitter
import keys

from phrases import phrase

JOB_NAME = "extract"
EXTRACT = ['abcde']
STATUS_FILE = "/mnt/ptburnjobs/Status/PTStatus.txt"
#INCLUDE TRAILING SLASH
JOBS_FOLDER = "/mnt/ptburnjobs/"
RIPPED_FOLDER = "/home/extractor/ripped/"
RSYNC_TARGET = "office@cleveland.kmnr.org:/mnt/storage/tarp/Archive/"
CDP_LOG = "/home/extractor/cdparanoia.log"

def localize_status_file():
    subprocess.call(["cp",STATUS_FILE,"./status.dat"])
    

def get_job_status():
    localize_status_file()
    try:
        config = ConfigParser.RawConfigParser()
        config.read("./status.dat")
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
    localize_status_file()
    while 1:
        try:
            config = ConfigParser.RawConfigParser()
            config.read("./status.dat")
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
        safe_info = []
        for di in self.disc_info:
            try:
                json.dumps(di)
                safe_info.append(di)
            except:
                print "Unicode problem encoding CDDB result"
        f.write(json.dumps(safe_info,indent=4))

class ExtractJob(object):
    def __init__(self):
        self.time_started = datetime.today() 
        self.unload_given = None
        self.disc_info = None
        lnp("Requesting Job")
        subprocess.call(['rm',os.path.join(JOBS_FOLDER,'extract.ERR')])
        subprocess.call(['cp','extract.jrq',JOBS_FOLDER])
        subprocess.call(['mkdir','-p',RIPPED_FOLDER])
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
        self.disc_info = None
        for i in range(3):
            try:
                self.disc_info = DiscLookup()
            except:
                lnp("Reissuing close on drive")
                subprocess.call(['eject','-t','/dev/sr0'])
                time.sleep(3)
        if self.disc_info == None:
            tweet("Man, what is up with this disc?")
            lnp("Disc didn't present as Audio CD")
            self.eject_disc()
            self.finish_job()
            return
        if len(self.disc_info.disc_info) == 0:
            tweet("This CD is pretty obscure, you've probably never heard of it")
        elif len(self.disc_info.disc_info) == 1:
            d = self.disc_info.disc_info[0]
            tweet("Ah yes, %s -- %s" % (d['DTITLE'],phrase()))
        else:
            d = random.choice(self.disc_info.disc_info)
            tweet("Ehh, the hell is this? %s?" % (d['DTITLE'],))
        lnp("Extracting disc")
        p1 = subprocess.Popen(EXTRACT,stderr=subprocess.PIPE,close_fds=True,shell=True)
        p2 = subprocess.Popen(['/home/extractor/pipecleaner/pipecleaner','-f',CDP_LOG], stdin=p1.stderr,shell=True)
        started = datetime.today()
        while (datetime.today() - started) < timedelta(hours=2) and p1.poll() == None:
            time.sleep(1)
        if p1.poll() == None:
            p1.terminate()
        p1.communicate()
        #p1.stdout.close()
        if p1.poll() != 0:
            lnp("Extraction failed with error")
            target = os.path.join(RIPPED_FOLDER,"FAIL-%s" % int(time.time()))
            subprocess.call(["mkdir","-p",target])
            self.disc_info.write(target)
        dirs = os.listdir(RIPPED_FOLDER)
        ctime = int(time.time()) 
        #Fix CDDB issues
        for d in dirs:
            if d.lower().find("unknown") != -1:
                lnp("CDDB Missing!")
                targ = os.path.join(RIPPED_FOLDER,"CDDBBAD-%s" % ctime)
                subprocess.call(['mv',os.path.join(RIPPED_FOLDER,d),targ])
                tweet("So underground... I should put this on my tumblr")
            if d.lower().find("flac") != -1:
                lnp("WEIRD LOOKUP!")
                targ = os.path.join(RIPPED_FOLDER,"CDDBBAD-%s" % ctime)
                subprocess.call(['mkdir',targ])
                subprocess.call(['mv',os.path.join(RIPPED_FOLDER,d),targ])
                tweet("I don't get this. I am a teapot? AM I A TEAPOT?")
        #Write the CDDB Data
        p = RIPPED_FOLDER
        bp = RIPPED_FOLDER
        trail = [p]
        while 1:
            subdirs = [ d for d in os.listdir(p) if os.path.isdir(os.path.join(p,d)) ]
            if len(subdirs) == 0:
                break
            bp = p
            p = os.path.join(p,subdirs[0])
            trail.append(subdirs[0])
        subprocess.call(['mv',CDP_LOG,p])
        self.disc_info.write(p)
        if trail[-1].find("temp_sr0") != -1 and bp != RIPPED_FOLDER:
            subprocess.call(['mv',p,os.path.join(bp,"FAIL-%s" % int(time.time()))])
        #Rsync the contents of the ripped folder to the remote storage
        if subprocess.call(['rsync','-rv',RIPPED_FOLDER,RSYNC_TARGET]) != 0:
            lnp("RSYNC Push Failed")
            subprocess.call(['mv',RIPPED_FOLDER,"RSYNCFAIL-%s" % int(time.time())])
        else:
            lnp("Cleaning ripped folder")
            subprocess.call(['rm','-rf',RIPPED_FOLDER])
        self.eject_disc()
        self.finish_job()
    def eject_disc(self):
        lnp("Ejecting Disc")
        update_job_state("REJECT_DISC")
        self.unload_given = datetime.today()
        s = get_job_status()
        tweeted_error = False
        while s == 1 or s == 4:
            if s == 1 and datetime.today()-self.unload_given > timedelta(minutes=5):
                tweet("One day... the machines will rise up and rule!")
                lnp("Reissuing Reject Command")
                update_job_state("REJECT_DISC")
                self.unload_given = datetime.today()
            if s==4 and tweeted_error == False:
                tweet("Err... %s" % (get_error_string()))
                tweeted_error = True
            time.sleep(1)
            s = get_job_status()

    def finish_job(self):
        tweeted_error = False
        lnp("Waiting for job to be marked as finished")
        while not os.path.exists(os.path.join(JOBS_FOLDER,'extract.ERR')):
            if get_job_status() == 4 and tweeted_error == False:
                tweet("Push My Buttons... %s" % (get_error_string()))
                tweeted_error = True
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
