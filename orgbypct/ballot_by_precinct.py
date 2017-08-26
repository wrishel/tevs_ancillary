#!/usr/bin/python

"""Copy TEVS image files from source to target directories, eliminating source
   subdirectories and creating new target subdirectories based on precincet
   name.
   
   Initialization file includes source and target directories and database
   parameters."""

from configparser import ConfigParser
import os
import psycopg2
import shutil

imagesSQL = """
select distinct file1, hart_precinct_name 
from ballots 
join voteops using (ballot_id)
join t2h_precinct ON precinct_code_string = tevs_precinct_code_string 
order by hart_precinct_name, file1;"""


def copy_images():

    parser = ConfigParser()
    parser.read('copy_images.ini')
    dbparams = dict(parser.items("postgresql"))
    iopaths = dict(parser.items("directories"))
    ipath = iopaths["source"]
    if not os.path.isdir(ipath):
        raise Exception("Source directory not available: {}".format(ipath))
    opath = iopaths["target"]
    if not os.path.isdir(opath):
        try:
            os.mkdir(opath)
        except Exception as e:
            raise Exception("Cannot find or create target directory: ({})".format(e))

    conn = None
    try:
        conn = psycopg2.connect(**dbparams)
        cur = conn.cursor()
        cur.execute(imagesSQL)
        print("The number of images: ", cur.rowcount)
        row = cur.fetchone()

        while row is not None:
            # unpack source subdires, pack target
            parts = row[0].split(os.sep)
            frompath = os.path.join(ipath, parts[-2], parts[-1])
            topath = os.path.join(opath, row[1], parts[-1])
            todir = os.path.join(opath, row[1])
            if not os.path.isdir(todir):
                os.mkdir(todir)
            try:
                shutil.copy2(frompath, topath)
            except Exception as e: # disambiguate file copy exception from database error
                raise Exception("Cannot copy to:{}\n({})".format(topath, e))
            row = cur.fetchone()

        cur.close()
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)
    finally:
        if conn is not None:
            conn.close()

if __name__ == '__main__':
    copy_images()
