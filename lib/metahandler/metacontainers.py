'''
create/install metadata containers,
v1.0
currently very specific to icefilms.info
'''

# NOTE: these are imported later on in the create container function:
# from cleaners import *
# import clean_dirs

import os,sys
import shutil
import xbmcvfs

#necessary so that the metacontainers.py can use the scrapers
try: import xbmc
except:
     xbmc_imported = False
else:
     xbmc_imported = True

from t0mm0.common.addon import Addon

#append lib directory
addon = Addon('script.module.metahandler')
addon_path = addon.get_path()
sys.path.append((os.path.split(addon_path))[0])

'''
   Use MySQL settings if applicable, else:
       Use SQLIte3 wherever possible, needed for newer versions of XBMC
       Keep pysqlite2 for legacy support
'''
try:
	if  addon.get_setting('use_remote_db')=='true' and \
	    addon.get_setting('db_address') is not None and \
	    addon.get_setting('db_user') is not None and \
	    addon.get_setting('db_pass') is not None and \
	    addon.get_setting('db_name') is not None:
		import mysql.connector as database
		addon.log('Metacontainers - Loading MySQLdb as DB engine', 2)
		DB = 'mysql'
	else:
		raise ValueError('MySQL not enabled or not setup correctly')
except:
	try: 
		from sqlite3 import dbapi2 as database
		addon.log('Metacontainers - Loading sqlite3 as DB engine', 2)
	except: 
		from pysqlite2 import dbapi2 as database
		addon.log('Metacontainers - pysqlite2 as DB engine', 2)
	DB = 'sqlite'

class MetaContainer:

    def __init__(self, path='special://profile/addon_data/script.module.metahandler'):
        #!!!! This must be matched to the path in meteahandler.py MetaData __init__

        #Check if a path has been set in the addon settings
        settings_path = addon.get_setting('meta_folder_location')
        
        if settings_path:
            self.path = xbmc.translatePath(settings_path)
        else:
            self.path = xbmc.translatePath(path)

        self.work_path = os.path.join(self.path, 'work')
        self.cache_path = os.path.join(self.path,  'meta_cache')
        self.videocache = os.path.join(self.cache_path, 'video_cache.db')
        self.work_videocache = os.path.join(self.work_path, 'video_cache.db')
        self.movie_images = os.path.join(self.cache_path, 'movie')
        self.tv_images = os.path.join(self.cache_path, 'tvshow')        
        
        self.table_list = ['movie_meta', 'tvshow_meta', 'season_meta', 'episode_meta']
     
        addon.log('---------------------------------------------------------------------------------------', 2)
        #delete and re-create work_path to ensure no previous files are left over
        if xbmcvfs.exists(self.work_path):
            import shutil
            try:
                addon.log('Removing previous work folder: %s' % self.work_path, 2)
                # shutil.rmtree(self.work_path)
                xbmcvfs.rmdir(self.work_path)
            except Exception, e:
                addon.log('Failed to delete work folder: %s' % e, 4)
                pass
        
        #Re-Create work folder
        self.make_dir(self.work_path)

               
    def get_workpath(self):
        return self._work_path


    def get_cachepath(self):
        return self._cache_path
            

    def make_dir(self, mypath):
        ''' Creates sub-directories if they are not found. '''
        if not xbmcvfs.exists(mypath): xbmcvfs.mkdirs(mypath)   


    def _del_metadir(self, path=''):

        if path:
            cache_path = path
        else:
            catch_path = self.cache_path
      
        #Nuke the old meta_caches folder (if it exists) and install this meta_caches folder.
        #Will only ever delete a meta_caches folder, so is farly safe (won't delete anything it is fed)

        if xbmcvfs.exists(catch_path):
                try:
                    shutil.rmtree(catch_path)
                except:
                    addon.log('Failed to delete old meta', 4)
                    return False
                else:
                    addon.log('deleted old meta', 0)
                    return True


    def _del_path(self, path):

        if xbmcvfs.exists(path):
                try:
                    shutil.rmtree(path)
                except:
                    addon.log('Failed to delete old meta', 4)
                    return False
                else:
                    addon.log('deleted old meta', 0)
                    return True


    def _extract_zip(self, src, dest):
            try:
                addon.log('Extracting '+str(src)+' to '+str(dest), 0)
                #make sure there are no double slashes in paths
                src=os.path.normpath(src)
                dest=os.path.normpath(dest) 

                #Unzip - Only if file size is > 1KB
                if os.path.getsize(src) > 10000:
                    xbmc.executebuiltin("XBMC.Extract("+src+","+dest+")")
                else:
                    addon.log('************* Error: File size is too small', 4)
                    return False

            except:
                addon.log('Extraction failed!', 4)
                return False
            else:                
                addon.log('Extraction success!', 0)
                return True


    def _insert_metadata(self, table):
        '''
        Batch insert records into existing cache DB

        Used to add extra meta packs to existing DB
        Duplicate key errors are ignored
        
        Args:
            table (str): table name to select from/insert into
        '''

        addon.log('Inserting records into table: %s' % table, 0)
        # try:
        if DB == 'mysql':
            try: 	from sqlite3  import dbapi2 as sqlite
            except: from pysqlite2 import dbapi2 as sqlite

            db_address = addon.get_setting('db_address')
            db_port = addon.get_setting('db_port')
            if db_port: db_address = '%s:%s' %(db_address,db_port)
            db_user = addon.get_setting('db_user')
            db_pass = addon.get_setting('db_pass')
            db_name = addon.get_setting('db_name')

            db = database.connect(db_name, db_user, db_pass, db_address, buffered=True)
            mysql_cur = db.cursor()
            work_db = sqlite.connect(self.work_videocache);
            rows = work_db.execute('SELECT * FROM %s' %table).fetchall()

            cur = work_db.cursor()
            rows = cur.execute('SELECT * FROM %s' %table).fetchall()
            if rows:
                cols = ','.join([c[0] for c in cur.description])
                num_args = len(rows[0])
                args = ','.join(['%s']*num_args)
                sql_insert = 'INSERT IGNORE INTO %s (%s) VALUES(%s)'%(table, cols, args)
                mysql_cur.executemany(sql_insert, rows)
            work_db.close()

        else:
            sql_insert = 'INSERT OR IGNORE INTO %s SELECT * FROM work_db.%s' % (table, table)        
            addon.log('SQL Insert: %s' % sql_insert, 0)
            addon.log(self.work_videocache, 0)
            db = database.connect(self.videocache)
            db.execute('ATTACH DATABASE "%s" as work_db' % self.work_videocache)
            db.execute(sql_insert)
        # except Exception, e:
            # addon.log('************* Error attempting to insert into table: %s with error: %s' % (table, e), 4)
            # pass
            # return False
        db.commit()
        db.close()
        return True

         
    def install_metadata_container(self, containerpath, installtype):

        addon.log('Attempting to install type: %s  path: %s' % (installtype, containerpath), 0)

        if installtype=='database':
            extract = self._extract_zip(containerpath, self.work_path)
            #Sleep for 5 seconds to ensure DB is unzipped - else insert will fail
            xbmc.sleep(5000)
            for table in self.table_list:
                install = self._insert_metadata(table)
            
            if extract and install:
                return True
                
        elif installtype=='movie_images':
            return self._extract_zip(containerpath, self.movie_images)

        elif installtype=='tv_images':
            return self._extract_zip(containerpath, self.tv_images)

        else:
            addon.log('********* Not a valid installtype: %s' % installtype, 3)
            return False
