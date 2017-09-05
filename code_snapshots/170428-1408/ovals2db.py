import psycopg2
import pdb
import sys

create_table = """create table cham2_ovals (
oval_id serial,
ballot_id integer default -1,
filename varchar,
v34_start smallint,
v34_end smallint,
v34_span smallint,
v34_tcount smallint,
v34_red_min smallint,
v34_red_max smallint,
v34_red_mean smallint,
v34_green_min smallint,
v34_green_max smallint,
v34_green_mean smallint,
v34_blue_min smallint,
v34_blue_max smallint,
v34_blue_mean smallint,

v54_start smallint,
v54_end smallint,
v54_span smallint,
v54_tcount smallint,
v54_red_min smallint,
v54_red_max smallint,
v54_red_mean smallint,
v54_green_min smallint,
v54_green_max smallint,
v54_green_mean smallint,
v54_blue_min smallint,
v54_blue_max smallint,
v54_blue_mean smallint,

v74_start smallint,
v74_end smallint,
v74_span smallint,
v74_tcount smallint,
v74_red_min smallint,
v74_red_max smallint,
v74_red_mean smallint,
v74_green_min smallint,
v74_green_max smallint,
v74_green_mean smallint,
v74_blue_min smallint,
v74_blue_max smallint,
v74_blue_mean smallint,

h28_start smallint,
h28_end smallint,
h28_span smallint,
h28_tcount smallint,
h28_red_min smallint,
h28_red_max smallint,
h28_red_mean smallint,
h28_green_min smallint,
h28_green_max smallint,
h28_green_mean smallint,
h28_blue_min smallint,
h28_blue_max smallint,
h28_blue_mean smallint,

h36_start smallint,
h36_end smallint,
h36_span smallint,
h36_tcount smallint,
h36_red_min smallint,
h36_red_max smallint,
h36_red_mean smallint,
h36_green_min smallint,
h36_green_max smallint,
h36_green_mean smallint,
h36_blue_min smallint,
h36_blue_max smallint,
h36_blue_mean smallint,

h44_start smallint,
h44_end smallint,
h44_span smallint,
h44_tcount smallint,
h44_red_min smallint,
h44_red_max smallint,
h44_red_mean smallint,
h44_green_min smallint,
h44_green_max smallint,
h44_green_mean smallint,
h44_blue_min smallint,
h44_blue_max smallint,
h44_blue_mean smallint,
valid boolean default True,
crop_x smallint default -1,
crop_y smallint default -1
);
"""
insert_csv = """insert into cham2_ovals (
filename,

v34_start ,
v34_end ,
v34_span ,
v34_tcount ,
v34_red_min ,
v34_red_max ,
v34_red_mean ,
v34_green_min ,
v34_green_max ,
v34_green_mean ,
v34_blue_min ,
v34_blue_max ,
v34_blue_mean ,

v54_start ,
v54_end ,
v54_span ,
v54_tcount ,
v54_red_min ,
v54_red_max ,
v54_red_mean ,
v54_green_min ,
v54_green_max ,
v54_green_mean ,
v54_blue_min ,
v54_blue_max ,
v54_blue_mean ,

v74_start ,
v74_end ,
v74_span ,
v74_tcount ,
v74_red_min ,
v74_red_max ,
v74_red_mean ,
v74_green_min ,
v74_green_max ,
v74_green_mean ,
v74_blue_min ,
v74_blue_max ,
v74_blue_mean ,

h28_start ,
h28_end ,
h28_span ,
h28_tcount ,
h28_red_min ,
h28_red_max ,
h28_red_mean ,
h28_green_min ,
h28_green_max ,
h28_green_mean ,
h28_blue_min ,
h28_blue_max ,
h28_blue_mean ,

h36_start ,
h36_end ,
h36_span ,
h36_tcount ,
h36_red_min ,
h36_red_max ,
h36_red_mean ,
h36_green_min ,
h36_green_max ,
h36_green_mean ,
h36_blue_min ,
h36_blue_max ,
h36_blue_mean ,

h44_start ,
h44_end ,
h44_span ,
h44_tcount ,
h44_red_min ,
h44_red_max ,
h44_red_mean ,
h44_green_min ,
h44_green_max ,
h44_green_mean ,
h44_blue_min ,
h44_blue_max ,
h44_blue_mean,

ballot_id,
crop_x,
crop_y 

) values (
%s, 

%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 
%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 
%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 

%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 
%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 
%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
%s, %s, %s
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
            self.conn.rollback()


if __name__ == "__main__":
    fields_per_csv_line = 1 + (13*6) + 3
    # open database
    po = PostgresDB(database="mitch",host="/home/mitch/pg2",port=6432)
    # try creating table
    po.create_table_if_absent()
    # open next csv file
    csv = open(sys.argv[1],"r")
    # read each line, split into field array, add array values to db
    for line in csv.readlines():
        # trim the leading [, the trailing \n and the trailing ], all squot, spc
        line = line[1:-2].replace("'","").replace(" ","")
        fields = line.split(",")
        filename = fields[0]
        ballot_id = '9'+filename[1:6]
        crop_x = filename[7:11]
        crop_y = filename[12:16]
        fields = filter(lambda x: not x.startswith("["), fields)
        fields.extend([ballot_id,crop_x,crop_y])
        fieldlist = []
        fieldlist.append(fields[0])
        fieldlist.extend(fields[2:])
        fields = fieldlist
        #print insert_csv
        #print fieldlist
        if len(fields)<>fields_per_csv_line:
            print "Field count not %d\n on line %s" % (fields_per_csv_line,line)
            pdb.set_trace()
            continue
        try:
            po.insert_from_fields(fields)
        except Exception as e:
            print e
            pdb.set_trace()
