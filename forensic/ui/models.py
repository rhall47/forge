'''
Copyright 2013-2014 Hannu Visti

This file is part of ForGe forensic test image generator.
ForGe is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with ForGe.  If not, see <http://www.gnu.org/licenses/>.
'''

from django.db import models

from django.core.files.storage import default_storage
import sys,os
import random
import shutil
import uitools
from uitools import ForensicError
from uitools import Chelper
from subprocess import call
import datetime
import importlib

class User(models.Model):
    ROLES = ((0,"Administrator"), (1,"Teacher"), (2,"Student"), (3,"Tester"))
    name = models.CharField(max_length=64, unique=True)
    role = models.IntegerField(choices=ROLES)
    valid_until = models.DateField('valid until')

    def __unicode__(self):
        return self.name
    

class FileSystem(models.Model):
    name = models.CharField(max_length=32, unique=True)
    pythonpath = models.CharField(max_length=192, blank=True)
    pythoncreatecommand = models.CharField(max_length=64, blank=True, verbose_name="create")
    fsclass = models.CharField(max_length = 32)
    def __unicode__(self):
        return self.name
    def get_create_function(self):
        try:
            func = self._create_function_name
        except AttributeError:
            h = importlib.import_module(self.pythonpath)
            
            self._create_function_name = getattr(h, self.pythoncreatecommand)
            func = self._create_function_name
        return func
    def get_class(self):
        try:
            cl = self._class_instance
        except AttributeError:
            h = importlib.import_module(self.pythonpath)
            self._class_instance = getattr(h, self.fsclass)
            cl = self._class_instance
        return cl
    
        
    
class HidingMethod(models.Model):
    name = models.CharField(max_length=32, unique=True)
    priority = models.IntegerField(default=0)
    pythonpath = models.CharField(max_length=256, blank=True)
    pythonhideclass = models.CharField(max_length=256, blank=True)

    def __unicode__(self):
        return self.name
    def get_hide_class(self):
        try:
            func = self._hide_class_name
        except AttributeError:
            h = importlib.import_module(self.pythonpath)
            
            self._hide_class_name = getattr(h, self.pythonhideclass)
            func = self._hide_class_name
        return func

class WebMethod(models.Model):
    name = models.CharField(max_length=32, unique=True)
    priority = models.IntegerField(default=0)
    pythonpath = models.CharField(max_length=256, blank=True)
    pythonhideclass = models.CharField(max_length=256, blank=True)
    def __unicode__(self):
        return self.name

    def get_hide_class(self):
        try:
            func = self._hide_class_name
        except AttributeError:
            h = importlib.import_module(self.pythonpath)
            
            self._hide_class_name = getattr(h, self.pythonhideclass)
            func = self._hide_class_name
        return func

class TrivialFileItem(models.Model):
    TYPES = ((0,"Image"), (1,"Document"), (2,"Email"), (3,"Web"), (4,"Audio"), (5, "Video"), 
             (6, "Program"), (7,"Unsorted"), (8,"Text"), (9,"Archive"))
    name = models.CharField(max_length =  256)
    type = models.IntegerField(choices=TYPES)
    file = models.FileField(upload_to = "repository")
    def __unicode__(self):
        return self.name

class SecretFileItem(models.Model):    
    name = models.CharField(max_length = 64)
    file = models.FileField(upload_to = "secretrepository")
    group = models.IntegerField(default=0)
    def __unicode__(self):
        return self.name

class Webhistory(models.Model):
    name = models.CharField(max_length = 256, unique=True)
    date_created = models.DateField('date created')
    exact = models.BooleanField(default=True)
    method = models.ForeignKey(WebMethod)
    ntocreate = models.IntegerField("n",default=1)
    def __unicode__(self):
        return self.name

    def getLongFilename(self,fname):        
        return Chelper().prefix+"/"+fname

    def processWebhistory(self):
        try:
            self.filesystem = FileSystem.objects.filter(name="NTFS")[0]
        except:
            raise ForensicError("no NTFS")

        t_urls = self.url_set.filter(group = 0)
        s_urls = self.url_set.exclude(group = 0)
        t_searches = self.searchengine_set.filter(group=0)
        s_searches = self.searchengine_set.exclude(group=0)
        command = self.filesystem.get_create_function()
        fsclass = self.filesystem.get_class()
        mountpoint = Chelper().mountpoint
        prefix = Chelper().prefix


        uclass = self.method.get_hide_class()
        webm = uclass(self.filesystem)

        rdict = webm.hide_url(trivial_urls=t_urls,secret_urls=s_urls,
                              amount=self.ntocreate,
                              secret_searches=s_searches, trivial_searches=t_searches)
        if rdict["status"] == 2:
            raise ForensicError(rdict["message"])

        i=0
        failed_list=[]
        for r in rdict["results"]:
            i += 1
            if r["status"] != "OK":
                continue

            iname=self.name+"-"+str(i)
            fcr =  command(size=r["size"], garbage=False,
                           clustersize=8, 
                           name=iname)
            if fcr != 0:
                uitools.errlog( "something may be wrong, image not created")
                failed_list.append([i,"Unable to create image file"])
                continue
            mount_file = self.getLongFilename(iname)
            fsystem = fsclass(mount_file, mountpoint)
            fsystem.fs_init()
            if fsystem.mount_image() != 0:
                failed_list.append([i,"Cannot mount image file"])
                uitools.errlog("--- Cannot mount file, image not processed")
                os.remove(mount_file)
                continue
            try:
                cdir=os.getcwd()
                os.chdir(mountpoint)
            except:
                fsystem.dismount_image()
                os.remove(mount_file)
                failed_list.append([i, "unable to change directory"])
                continue
            cres = call(["/bin/tar", "xf", r["fname"]], shell=False)
            if cres != 0:
                uitools.errlog("Unable to untar %s" % r["fname"])
                fsystem.dismount_image()
                os.remove(mount_file)
                failed_list.append([i, "unable to untar"])
                continue
            os.chdir(cdir)
            fsystem.dismount_image()

class Url(models.Model):
    case = models.ForeignKey(Webhistory)
    url = models.CharField(max_length = 1024)
    num_clicks = models.IntegerField(default=1)
    click_depth = models.IntegerField(default=1)
    date_clicked = models.DateField('date clicked')
    group = models.IntegerField(default=0)

class SearchEngine(models.Model):
    case = models.ForeignKey(Webhistory)
    ENGINES=((0,"Google"), (1,"Yahoo"),(2,"Bing"))
    engine = models.IntegerField(choices=ENGINES, default=0)
    search_string = models.CharField(max_length = 256)
    date_clicked = models.DateField('date clicked')
    group = models.IntegerField(default=0)
    click_result = models.IntegerField(default=0)
    click_depth = models.IntegerField(default=1)

class Case(models.Model):
    name = models.CharField(max_length = 256, unique=True)
    owner = models.ForeignKey(User)
    date_created = models.DateField('date created')
    filesystem = models.ForeignKey(FileSystem)
    size = models.CharField(max_length = 20)
    amount = models.PositiveIntegerField(verbose_name="Number of copies", blank=True, null=True)
    sweep = models.ForeignKey('SecretStrategy',blank=True, null=True)
    roottime = models.DateTimeField()
    weekvariance = models.IntegerField(default=0)
    garbage = models.BooleanField(default=False)
    fsparam1 = models.IntegerField(blank=True, default=0, verbose_name="Sectors per cluster")
    fsparam2 = models.IntegerField(blank=True, default=0)
    fsparam3 = models.IntegerField(blank=True, default=0)
    fsparam4 = models.IntegerField(blank=True, default=0)
    fsparam5 = models.IntegerField(blank=True, default=0)

    def __unicode__(self):
        return self.name

    def number_of_images(self):
        if self.sweep == None and self.amount == None:
            raise ForensicError("You must set either sweep or copies")
        if self.sweep != None:
            sweep = 1
        else:
            sweep = 0
        if self.amount != None:
            amount = self.amount
        else:
            amount = 0

        if (sweep == 0 and amount == 0) or (sweep != 0 and amount != 0):
            uitools.errlog("You must set either sweep or copies")
            return -1

        sstrat=[]
        if sweep > 0:
            fgroup = self.sweep.group
            sfiles = SecretFileItem.objects.filter(group=fgroup)

        return len(sfiles) if sweep > 0 else amount

    def processCase(self):

        trivial_strategies = self.trivialstrategy_set.all()
        secret_strategies_pre = self.secretstrategy_set.all()
        secret_strategies = secret_strategies_pre
        command = self.filesystem.get_create_function()
        fsclass = self.filesystem.get_class()
        mountpoint = Chelper().mountpoint
        prefix = Chelper().prefix

        failed_list=[]
        succeed_list = []

        tobecreated = self.number_of_images()
        if tobecreated == -1:
            failed_list.append([0,"You must set either sweep or number of copies but not both"])
            return [succeed_list,failed_list]

        if command == None:
            uitools.errlog("no FS create command")
            return None
        try:
            removed_chmod = os.chmod
            del os.chmod
        except AttributeError:
            removed_chmod = None
        if self.sweep != None:
            secretfiles = SecretFileItem.objects.filter(group=self.sweep.group)
            secretindex=0

        for i in range(1,tobecreated+1):
            if self.trivialstrategy_set.count() == 0:
                failed_list.append([i,"No trivial strategies"])
                continue
            filename = self.name+"-"+str(i)
            
            result =  command(size=self.size, garbage=self.garbage, 
                              clustersize=self.fsparam1, 
                              name=filename)
            if result != 0:
                uitools.errlog( "something may be wrong, image not created")
                failed_list.append([i,"Unable to create image file"])
                continue
            image = Image(filename=filename, seqno = i, case = self)
            image.save()
            mount_file = image.getLongFilename()
            fsystem = fsclass(mount_file, mountpoint)
            fsystem.fs_init()
            if fsystem.mount_image() != 0:
                failed_list.append([i,"Cannot mount image file"])
                uitools.errlog("--- Cannot mount file, image not processed")
                os.remove(mount_file)
                image.delete()
                continue
            """ Set root dir time """
            rand_weeks = random.randint(0,self.weekvariance)
            image.weekvariance = rand_weeks
            image.save()
            timevariance = datetime.timedelta(weeks=rand_weeks)
            image_time = self.roottime + timevariance
            time_command_list = []
            time_command_list = [["/.",image_time]]
            flag = False
            for strategy in trivial_strategies:
                try:
                    tl = image.implement_trivial_strategy(strategy, strategy.dirtime+timevariance)
                    time_command_list.append([strategy.path,strategy.dirtime+timevariance])
                    time_command_list = time_command_list + tl
                except ForensicError as fe:
                    failed_list.append([i,fe])
                    uitools.errlog(fe)
                    fsystem.dismount_image()
                    os.remove(mount_file)
                    image.delete()
                    flag = True
                    break
            if flag == True:
                continue
                
            """ Initialise NTFS structures at this stage """
            fsystem.dismount_image()
            fsystem.fs_init()

            """ 
            Reserve code for placeall implementation. 


            flag = False
            secret_strategies = []
            for st in secret_strategies_pre:
                if st.placeall:
                    if st == self.sweep:
                        uitools.errlog("Sweep strategy cannot be a placeall strategy")
                        failed_list.append([i,"Secret strategy cannot be a placeall strategy"])
                        os.remove(mount_file)
                        image.delete()
                        flag = True
                        break
                    pafiles = SecretFileItem.objects.filter(group=st.group)
                    
                else:
                    secret_strategies.append(st)
            if flag == True:
                continue """



            file_delete_list = []
            file_action_list = []    

            try:
                for prio in range (1,21):
                    current_strategies = [t for t in secret_strategies if t.method.priority == prio]
                    for sstrategy in current_strategies:
                        if self.sweep != None:
                            if sstrategy == self.sweep:
                                tv = image.implement_secret_strategy(sstrategy, fsystem, timevariance, 
                                                                     sfile = secretfiles[secretindex])
                                secretindex += 1
                            else:
                                tv = image.implement_secret_strategy(sstrategy, fsystem, timevariance, 
                                                                     sfile = None)
                        else:
                            tv = image.implement_secret_strategy(sstrategy, fsystem, timevariance, 
                                                                 sfile = None)
                        if tv:
                            try:
                                time_command_list = time_command_list + tv["timeline"]
                            except KeyError:
                                pass
                            try:
                                file_delete_list = file_delete_list + tv["todelete"]
                            except KeyError:
                                pass
                            try: 
                                file_action_list = file_action_list + tv["actions"]
                            except KeyError:
                                pass
                            
            except ForensicError as fe:
                failed_list.append([i,fe])
                uitools.errlog(fe)
                fsystem.dismount_image()
                os.remove(mount_file)
                image.delete()
                continue
                        
            """ Implement deletions 
            First a dummy is written to the root directory to make sure the files entered last
            are not deleted """
            if fsystem.mount_image() != 0:
                failed_list.append([i,"Cannot mount image for deletions"])
                uitools.errlog("cannot mount for deletions")
                image.delete()
                os.remove(mount_file)
                continue
            try:
                dfile = open(mountpoint+"/info.txt","w")
                dfile.write("Created by Forensic test image generator")
                dfile.write("Case %s, image %d" % (self.name,i))
                dfile.close()
            except IOError:
                failed_list.append([i,"Cannot write copyright"])
                uitools.errlog("Cannot write copyright. Not proceeding")
                fsystem.dismount_image()
                image.delete()
                os.remove(mount_file)
                continue
             
            """ flag = temporary variable to detect errors """
            flag = False    
            for dfile in file_delete_list:
                try:
                    os.remove(dfile)
                except (IOError,OSError):
                    failed_list.append([i,"Cannot delete file %s" % dfile])
                    uitools.errlog("cannot delete file")
                    fsystem.dismount_image()
                    image.delete()
                    os.remove(mount_file)
                    flag = True
                    break
            if flag:
                continue
            fsystem.dismount_image() 
            
            
            """ read FS structures once more from scratch """
            del fsystem           

            fsystem = fsclass(mount_file, mountpoint)
            fsystem.fs_init()
            flag = False
            """ Implement time """
            for ti in time_command_list:
                try:
                    pass
                    fsystem.change_time(ti[0],dict(all=ti[1]))
                except ForensicError as fe:
                    failed_list.append([i,fe])
                    uitools.errlog(fe)
                    os.remove(mount_file)
                    image.delete()
                    flag = True
                    break
            if flag:
                continue
            
            del fsystem
            fsystem = fsclass(mount_file,mountpoint)
            fsystem.fs_init()
            """ implement actions """
            flag = False
            for act in file_action_list:
                try:
                    fsystem.implement_action(act)
                except ForensicError as fe:
                    failed_list.append([i,fe])
                    uitools.errlog(fe)
                    os.remove(mount_file)
                    image.delete()
                    flag = True
                    break
            if flag:
                continue
            
            """ Finally - do file system specific cleanup actions 
                for NTFS this means setting . in $MftMirr to correspond to $Mft """    
            try:
                fsystem.fs_finalise()
            except ForensicError as fe:
                failed_list.append([i,fe])
                uitools.errlog(fe)
                os.remove(mount_file)
                image.delete()
                continue               
            succeed_list.append(i)
        if removed_chmod != None:
            setattr(os, "chmod", removed_chmod)
        return [succeed_list,failed_list]
            
class TrivialStrategy(models.Model):
    TYPES = ((0,"Image"), (1,"Document"), (2,"Email"), (3,"Web"), (4,"Audio"), (5, "Video"), 
             (6, "Program"), (7,"Unsorted"), (8,"Text"), (9,"Archive"))
    case = models.ForeignKey(Case)
    type = models.IntegerField(choices=TYPES)
    exact = models.BooleanField(default=True)
    quantity = models.IntegerField()
    path = models.CharField(max_length=256)
    dirtime = models.DateTimeField()
    class Meta:
        unique_together = ('case', 'path',)
    
    def __unicode__(self):
        return self.case.name+":"+str(self.type)+":"+self.path
    
class SecretStrategy(models.Model):
    ACTIONS=((0,"None"), (1,"Copy"),(2,"Move"),(3,"Rename"), (4,"Read"), (5,"Edit"))
    caseref = models.ForeignKey(Case)    
    method = models.ForeignKey(HidingMethod)
    group = models.IntegerField(default=0)
    amount = models.IntegerField(default=1)
    placeall = models.BooleanField(default=False)
    filetime = models.DateTimeField (blank=True, null=True)
    actiontime = models.DateTimeField(blank=True, null=True)
    action = models.IntegerField(choices=ACTIONS,blank=True, null=True)
    instruction = models.CharField(max_length=512, blank=True)

    
    def process_parameters(self):
        param={}
        for i in self.instruction.split():
            try:
                k,v = i.split(":")
                param[k] = v
            except ValueError:
                continue
        return param
        
    def __unicode__(self):
        return self.method.name+":"+str(self.group)
    
    
class Image(models.Model):
    seqno = models.IntegerField()
    case = models.ForeignKey(Case)
    filename = models.CharField(max_length=256, blank=True)
    weekvariance = models.IntegerField(blank=True, default=0)

    def __unicode__(self):
        return self.filename
    
    def getLongFilename(self):        
        return Chelper().prefix+"/"+self.filename
    
    def implement_trivial_strategy(self, strategy, dirtime):
        mountpoint = Chelper().mountpoint

        initialdelta = datetime.timedelta(seconds=random.randint(5,360))
        ''' Time difference of directory files will be randomly 0-3 seconds ''' 
        filedelta = datetime.timedelta(seconds=random.randint(0,3))
        inittime = dirtime + initialdelta
        time_command_list=[]
        files = []
        file_candidates = TrivialFileItem.objects.filter(type = strategy.type)
        if len(file_candidates) == 0:
            raise ForensicError("no trivial files of chosen type")
        pull_number = strategy.quantity
        if not strategy.exact:
            pull_number = random.randint(strategy.quantity, strategy.quantity*2)
        try:
            files = random.sample(file_candidates, pull_number)
        except ValueError:
            files = file_candidates
        
        strategypath = mountpoint+strategy.path
        try:
            if not os.path.exists(strategypath):
                os.makedirs(strategypath)
                #time_command_list.append([strategypath, dirtime])
                
        except OSError:
            raise ForensicError("cannot create trivial directory")
            

        for f in files:
            path = f.file.path
            try:
                shutil.copy(path,strategypath)
                tro = TrivialObject(image=self,file=f,path=strategy.path+"/"+f.name, inuse=False)
                tro.save()
                b = path.rsplit("/",1)[1]
                time_command_list.append([strategy.path+"/"+b,inittime])
                #print >>sys.stderr, "=", path, f.name

                inittime = inittime+filedelta
            except IOError:
                raise ForensicError("IO error / out of space")        
        return time_command_list
    
    def implement_secret_strategy(self,strategy, filesystem,timevariance, sfile=None):
        """ this is a kludge to initialise a class variable without __init__ """
        try:
            if self._used_items[0] == None:
                pass
        except (IndexError,NameError,AttributeError):
            self._used_items = []
            
        hiding_method = strategy.method
        #uitools.errlog(hiding_method.name)
        hcmodel = hiding_method.get_hide_class()
        ssclass = hcmodel(filesystem)

        if not sfile:
            try:
                file_candidates = SecretFileItem.objects.filter(group = strategy.group)
                i = 0
                """ first try to find a random file. Fall back to sequential if 20 tries fail """
                while i < 20:
                    hfile = random.choice(file_candidates)
                    if not hfile in self._used_items:
                        self._used_items.append(hfile)
                        break
                    i += 1
                if i == 20:
                    """ find something if nothing found """
                    possibilities = list(set(file_candidates) - set(self._used_items))
                    if possibilities == []:
                        raise ForensicError("no files left to be hidden")
                    else:
                        hfile = possibilities[0]
                        self._used_items.append(hfile)
                
            except (IndexError, NameError):
                raise ForensicError("No files to be hidden")

        else:
            hfile = sfile
            
        retv = None
        try:
            result = ssclass.hide_file(hfile.file, self, strategy.process_parameters())
            if result:
                ho = HiddenObject(image=self,file=hfile,method=hiding_method, location=result["instruction"])
                ho.save()
                retv = {}
                try:
                    trivial_file_path = result["path"]
                    try:
                        if result["newfile"] == True:
                            pass
                        else:
                            self.mark_trivial_file_used(trivial_file_path)
                    except KeyError:
                        self.mark_trivial_file_used(trivial_file_path)
                except KeyError:
                    pass
                    
                try:
                    retv["todelete"] = result["todelete"]
                except KeyError:
                    pass
                if strategy.filetime:
                    try:
                        retv["timeline"] = [[result["path"],strategy.filetime+timevariance]]
                        ho.filetime = strategy.filetime + timevariance
                        ho.save()
                        #retv.append([result["path"],strategy.filetime])
                    except KeyError:
                        pass
                if strategy.actiontime and strategy.action:
                    helper = strategy.ACTIONS[strategy.action][1]
                    pblock = {}
                    pblock[helper] = strategy.actiontime + timevariance
                    try:
                        retv["actions"] = [[result["path"],pblock]]
                        newinstr = ho.location + " ACTION: %s on %s" % (helper,pblock[helper])
                        ho.location = newinstr
                        ho.save()
                    except KeyError:
                        """ no result["path"] - maybe file slack? """
                        pass
                
            else:
                raise ForensicError("hiding method resulted nothing. Unable to hide")
                                    
                    
        except ForensicError as fe:
            uitools.errlog(fe)
            #ho.delete()
            raise
        return retv
        #    uitools.errlog("Not hidden, no candidate files")
            
    def find_trivial_files_by_ext(self, extensions):
        trivial_objects = TrivialObject.objects.filter(image = self)
        cset = []
        for t in trivial_objects:
            if t.is_of_type(extensions) == True:
                cset.append(t.path)
        return cset

    def mark_trivial_file_used(self, path):
        trivial_objects = TrivialObject.objects.filter(image = self)
        for t in trivial_objects:
            if t.path == path:
                t.inuse = True
                t.save()
                return
        raise ForensicError("Unable to mark %s used" % path)

    def check_trivial_usage_status(self, tpath):
        tfile = TrivialObject.objects.filter(image=self, path = tpath)[0]
        return tfile.inuse
    
class TrivialObject(models.Model):
    image = models.ForeignKey(Image)
    file = models.ForeignKey(TrivialFileItem)
    path = models.CharField(max_length=256)
    inuse = models.BooleanField(default=False)

    class Meta:
        unique_together = ("image", "path")
    
    def __unicode__(self):
        return self.path

    def is_of_type(self, reqtype):
        if type(reqtype) is not list:
            raise ForensicError("request type must be a list")
        try:
            filename = self.file.name
            extension = filename.rsplit(".",1)[1]
        except IndexError:
            return False
        if extension in reqtype:
            return True
        else:
            return False
        
class HiddenObject(models.Model):
    ACTIONS=((0,"None"), (1,"Copy"),(2,"Move"),(3,"Rename"), (4,"Read"), (5,"Edit"))
    image = models.ForeignKey(Image)
    file = models.ForeignKey(SecretFileItem)
    method = models.ForeignKey(HidingMethod)
    filetime = models.DateTimeField(blank=True, null=True)
    actiontime = models.DateTimeField(blank=True, null=True)
    action = models.IntegerField(choices=ACTIONS,blank=True, null=True)
    location = models.CharField(max_length = 1024, blank=True)
    
    def __unicode__(self):
        return self.image.filename+":"+self.location
    
