import Image
import psycopg2
import pdb
import sys

class PostgresDB(object):
    def __init__(self, database, host, port):
        self.conn = psycopg2.connect(database=database, host=host, port=port)

    def close(self):
        try:
            self.conn.close()
        except DatabaseError: 
            pass

    def query(self, q, *a):
        "returns a list of all results of q parameterized with a"
        cur = self.conn.cursor()
        cur.execute(q, *a)
        r = list(cur)
        cur.close()
        return r

    def query1(self, q, *a):
        "return one result from q parameterized with a"
        cur = self.conn.cursor()
        cur.execute(q, *a)
        r = cur.fetchone()
        cur.close()
        return r

if __name__ == "__main__":
    rootdir = "/media/CHAMPAIGN2/results/"
    width = 108
    height = 74
    xgrid = 10
    ygrid = 20
    po = PostgresDB(database="mitch",host="/home/mitch/pg2",port=6432)
    try:
        conditionsfile = open(sys.argv[1],"r")
        conditions = conditionsfile.read()
    except Exception as e:
        print e
        pdb.set_trace()
    query = """select cham2_ovals.filename,
            v54_red_min from cham2_ovals join cham2b_ovals 
       	    on cham2_ovals.ballot_id = cham2b_ovals.ballot_id 
	    and cham2_ovals.crop_x = cham2b_ovals.adj_x 
	    and cham2_ovals.crop_y = cham2b_ovals.adj_y where """ + conditions
    print query
    r = po.query(query)
    print "Results count:",len(r)
    print r[0:7]
    montage = Image.new("RGB",(width*xgrid,height*ygrid),(255,255,255))
    xoff = 0
    yoff = 0
    zoff = 0
    for retval in r:
        filename = retval[0]
        ballotnum = filename.split("_")[0]
        dirnum = ballotnum[0:3]
        filepath = "%s%s/%s" % (rootdir,dirnum,filename)
        try:
            im = Image.open(filepath)
            montage.paste(im,(xoff,yoff))
            xoff += width
            if xoff > (width*(xgrid-1)):
                xoff = 0
                yoff += height
                if yoff > (height*(ygrid-1)):
                    yoff = 0
                    mname = "%s_%d.jpg" % (sys.argv[1],zoff)
                    print "Saving",mname
                    montage.save(mname)
                    zoff += 1
                    if zoff > 10:
                        pdb.set_trace()
                    montage = Image.new("RGB",(width*xgrid,height*ygrid),(255,255,255))
        except Exception as e:
            print e
            continue
    mname = "%s_%d.jpg" % (sys.argv[1],zoff)
    print "Saving final ",mname
    montage.save(mname)
