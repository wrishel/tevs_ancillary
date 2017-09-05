try:
    import psycopg2 as DB
    DatabaseError = DB.DatabaseError
except ImportError:
    DatabaseError = Exception
    pass

import pdb
class NullDB(object):
    def __init__(self, *_):
        pass
    def close(self):
        pass
    def insert(self, _):
        pass


class PostgresDB(object):
    def __init__(self, name, user):
        self.conn = DB.connect(database=name, user=user)

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

    def getcac(self):
        #NB all db queries are decalred as strings after the method body for
        #clarity

        cur = self.conn.cursor()
        # get all voteops was_voted
        #try:
        #    cur.execute("""drop table contestsandchoices""")
        #except DB.ProgrammingError, e:
        #    print e
        #try:
        #    cur.execute("""drop sequence contestsandchoices_id_seq""")
        #except DB.ProgrammingError, e:
        #    print e
        cur.execute("""select * into vectors from ballots where ballot_id > 151969;""")
        cur.execute("""alter table vectors add column vector varchar(256) default 0""")
        cur.execute("""create sequence contestsandchoices_id_seq;""")
        cur.execute("""create table contestsandchoices (matchstring varchar(40),id int default nextval('contestsandchoices_id_seq'))""")
        # retrieve all contest and choice substrings in defined order
        cur.execute("""insert into contestsandchoices  (select substring(contest_text,1,20)||substring(choice_text,1,20) from ballots join voteops on ballots.ballot_id = voteops.ballot_id where ballots.ballot_id > 151969 group by substring(contest_text,1,20)||substring(choice_text,1,20) order by substring(contest_text,1,20)||substring(choice_text,1,20))""")
        #sql_ret = cur.fetchall()

        for x in range(153000,166728):
            # convert contest and choice substrings to integers, order by voteop_id
            print x,
            cur.execute("""select substring(contest_text,1,20)||substring(choice_text,1,20) as matchstring, b.ballot_id from voteops v join ballots b on v.ballot_id = b.ballot_id where was_voted and b.ballot_id = %d order by voteop_id"""%(x,))
            sql_ret = cur.fetchall()
            consolidated = ""
            for record in sql_ret:
                cur.execute("""select id from contestsandchoices where matchstring = '%s'""" % record[0])
                ret2 = cur.fetchall()
                try:
                    cac_number = ret2[0][0]
                except IndexError:
                    continue
                # append the cac number to write a consolidated number as text 
                consolidated = "%s%d," % (consolidated,cac_number)
            # when bit string has one bit set for each voted contest/choice,
            # set that bit string into vectors.vector for this ballot
            cur.execute("update vectors set vector = '%s' where ballot_id = %d" % (consolidated,x))
            print consolidated
            self.conn.commit()
        cur.execute("""select count(*) as num,vector into vector_counts from vectors group by vector order by vector""")
        cur.execute("""select num,vector from vector_counts where num > 1""")
        ret3 = cur.fetchall()
        for record in ret3:
            print 
            print "Count %d, vector %s" % (record[0],record[1])
            cur.execute("Select ballot_id from vectors where vector = '%s'" % (record[1]))
            ret4 = cur.fetchall()
            print ret4
if __name__ == "__main__":
    dbc = PostgresDB("mitch","mitch")
    dbc.getcac()
