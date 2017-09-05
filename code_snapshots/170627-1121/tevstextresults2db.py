import psycopg2
import pdb
import sys

create_table = """create table cham2b_ovals (
ovalb_id serial,
ballot_id integer default -1,
filename varchar,
layout_code varchar,
x smallint,
y smallint,
red_mean smallint,
red_lowest smallint,
red_low smallint,
red_high smallint,
red_highest smallint,
green_mean smallint,
green_lowest smallint,
green_low smallint,
green_high smallint,
green_highest smallint,
blue_mean smallint,
blue_lowest smallint,
blue_low smallint,
blue_high smallint,
blue_highest smallint,
adj_x smallint,
adj_y smallint);
"""
insert_csv = """insert into cham2b_ovals (
filename,
ballot_id,
layout_code,
x,
y,
red_mean ,
red_lowest ,
red_low ,
red_high ,
red_highest ,
green_mean ,
green_lowest ,
green_low ,
green_high ,
green_highest ,
blue_mean ,
blue_lowest ,
blue_low ,
blue_high ,
blue_highest,
adj_x,
adj_y 
 ) values (
%s,
%s,
%s,
%s,
%s,
%s, %s, %s, %s, %s, 
%s, %s, %s, %s, %s, 
%s, %s, %s, %s, %s,
%s, %s
);
"""
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

    def insert_from_fields(self,value_array):
        """insert one line of csv into oval table"""
        cur = self.conn.cursor()
        try:
            cur.execute(insert_csv, value_array)
            self.conn.commit()
        except Exception as e:
            print e
            self.conn.rollback()

    def create_table_if_absent(self):
        """ create oval table"""
        cur = self.conn.cursor()
        try:
            cur.execute(create_table)
            self.conn.commit()
        except psycopg2.ProgrammingError as e:
            print e
            pdb.set_trace()
            self.conn.rollback()


if __name__ == "__main__":
    fields_per_csv_line = 2 + 2 + 1 + (5*3) + 2
    # open database
    po = PostgresDB(database="mitch",host="/home/mitch/pg2",port=6432)
    # try creating table
    po.create_table_if_absent()
    # open next csv file
    file_template = "/media/CHAMPAIGN/results/%03d/%06d.txt"
    for filenum in range(200,100000,2):
        if (filenum % 100) == 1: print filenum
        next_csv_file = file_template % (filenum/1000,filenum)        
        try:
            csv = open(next_csv_file,"r")
        except IOError,e:
            print e
            continue
        # read each line, split into field array, add array values to db
        for line in csv.readlines():
            fields = line.split(",")
            fieldlist = []
            fieldlist.append(fields[0])
            fieldlist.append('9'+fields[0][29:34])
            fieldlist.extend(fields[1:2])
            fieldlist.extend(fields[5:7])
            r, g, b = 7,12,17
            adj = 22
            fieldlist.append(int(round(10*float(fields[r]))))
            fieldlist.extend(fields[r+1:r+5])
            fieldlist.append(int(round(10*float(fields[g]))))
            fieldlist.extend(fields[g+1:g+5])
            fieldlist.append(int(round(10*float(fields[b]))))
            fieldlist.extend(fields[b+1:b+5])
            fieldlist.extend(fields[22:24])
            if len(fieldlist)<>fields_per_csv_line:
                print "Field count not %d\n on line %s" % (fields_per_csv_line,line)
                pdb.set_trace()
                continue
            try:
                po.insert_from_fields(fieldlist)
            except Exception as e:
                print e
                pdb.set_trace()
