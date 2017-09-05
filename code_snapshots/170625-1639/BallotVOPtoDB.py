try:
    import psycopg2 as DB
    DatabaseError = DB.DatabaseError
except ImportError:
    DatabaseError = Exception
    pass

import pdb
import logging
import string

class NullDB(object):
    def __init__(self, *_):
        pass
    def close(self):
        pass
    def insert(self, _):
        pass


create_ballots_table = """
create table ballots (
                ballot_id serial PRIMARY KEY,
                processed_at timestamp,
                code_string varchar(80),
                layout_code bigint,
                file1 varchar(80),
                file2 varchar(80),
		precinct varchar(80),
		party varchar(80)
               );
"""
create_notes_table = """
create table notes (
                note_id serial PRIMARY KEY,
                ballot_id int REFERENCES ballots (ballot_id),
                filename varchar(128),
                x smallint,
                y smallint,
                w smallint,
                h smallint,
                note varchar(80),
                bg_color varchar(80)

               );
"""

create_voteops_table = """
create table voteops (
       voteop_id serial PRIMARY KEY,
       ballot_id int REFERENCES ballots (ballot_id),
       contest_text varchar(80),
       choice_text varchar(80),
       original_x smallint,
       original_y smallint,
       adjusted_x smallint,
       adjusted_y smallint,
       red_mean_intensity smallint,
       red_darkest_pixels smallint,
       red_darkish_pixels smallint,
       red_lightish_pixels smallint,
       red_lightest_pixels smallint,
       green_mean_intensity smallint,
       green_darkest_pixels smallint,
       green_darkish_pixels smallint,
       green_lightish_pixels smallint,
       green_lightest_pixels smallint,
       blue_mean_intensity smallint,
       blue_darkest_pixels smallint,
       blue_darkish_pixels smallint,
       blue_lightish_pixels smallint,
       blue_lightest_pixels smallint,
       was_voted boolean,
       image bytea,
       h_span smallint,
       v_span smallint,
       suspicious boolean default False,
       overvoted boolean default False,
       filename varchar(80),
       contest_text_id smallint default -1,
       contest_text_standardized_id smallint default -1,
       choice_text_id smallint default -1,
       choice_text_standardized_id smallint default -1,
       max_votes smallint default 1

);
"""
create_voteops_filename_index = """create index voteops_filename_index on voteops (filename);"""


class PostgresDB(object):
    def __init__(self, database, user):
        self.logger = logging.getLogger(__name__)
        try:
            self.conn = DB.connect(database=database, user=user, port=5433)
            self.logger.info("Connected to database %s as user %s" % (database,user))
        except Exception, e:
            # try to connect to user's default database
            try:
                self.conn = DB.connect(database=user, user=user)
            except Exception, e:
                self.logger.error("Could not connect to database %s specified in tevs.cfg,\nor connect to default database %s for user %s \nin order to create and initialize new database %s" % (database,user,user,database)) 
                self.logger.error("Do you have permission to create new databases?")
                self.logger.error(e)
            # try to create new database, close, and reconnect to new database
            try:
                # create database requires autocommit (cannot be in transaction)
                # if this fails, use shell cmd to psql to create db and tables
                # !!! WARNING, autocommit requires version 2.4.2 of psycopg2, 
                # not in Ubuntu 10.4.
                # must build and set symbolic link from pyshared 
                # to build/lib2.6/psycopg2
                # as Ubuntu may do something weird with python installations
                self.conn.autocommit = True
                # try to create new database
                self.query_no_returned_values(
                    "create database %s" % (database,) )
                self.conn.close()
                # exit on failure, reconnect to new on success
                self.conn = DB.connect(database=database, user=user)
            except Exception, e:
                print "Could not create or connect to database %s." % (database,)
                print "Does your version of python psycopg2 include autocommit?"
                print e
        try:
            self.query_no_returned_values(create_ballots_table)
            self.query_no_returned_values(create_notes_table)
            self.query_no_returned_values(create_voteops_table)
            self.query_no_returned_values(create_voteops_filename_index)
            self.logger.info(
                "Tables ballots, notes, and voteops now exist in db %s" % (
                    database,))
            # create tables in new database
        except Exception, e:
            self.logger.error( "Could not initialize database %s \nwith ballots and voteops tables, and voteops filename index." % (database,))
            self.logger.error(e)

    def close(self):
        try:
            self.conn.close()
        except DatabaseError: 
            pass


    def query_no_returned_values(self, q, *a):
        "returns a list of all results of q parameterized with a"
        cur = self.conn.cursor()
        try:
            cur.execute(q, *a)
            self.conn.commit()
        except DatabaseError, e:
            if -1 < string.find(str(e),"already exists"):
                self.logger.info("In query_no_return_values, db replied:" )
                self.logger.info(str(e))
            else:
                print q
                print e
                self.logger.warning("In query_no_return_values with query\n%s, \ngot error %s" % (q,e))

            self.conn.rollback()
        return 

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


    def insert_note(self,filename,ballot_id,x,y,w,h,note,bg_color):
        """Insert an annotation into the database"""
        insert_note = "insert into notes (filename, ballot_id, x, y, w, h, note, bg_color) values (%s, %s, %s, %s, %s, %s, %s, %s) returning note_id" 

        cur = self.conn.cursor()
        cur.execute(insert_note, (filename,ballot_id,x,y,w,h,note,bg_color))
        sql_ret = cur.fetchall()

        try:
            note_id = int(sql_ret[0][0])
            self.conn.commit()
        except ValueError as e:
            self.conn.rollback()
            raise DatabaseError("Corrupt note_id")
        return note_id

    def insert_new(self, ballot):
        """ create db records for ballot and individual vote ops of ballot"""
        cur = self.conn.cursor()
        name0 = ballot.side_list[0].image_filename
        try:
            name1 = ballot.side_list[1].image_filename
        except IndexError:
            name1 = None
        cur.execute(_pg_mk, (ballot.layout_id, 
                             name0, name1, 
                             ballot.precinct_id,
                             ballot.party_id
                             ))
        sql_ret = cur.fetchall()

        try:
            ballot_id = int(sql_ret[0][0])
        except ValueError as e:
            self.conn.rollback()
            raise DatabaseError("Corrupt ballot_id")

        for vop in ballot.results:
            try:
                cur.execute(_pg_ins, (
                        ballot_id,
                        vop.contest[:80],
                        vop.choice[:80],

                        vop.crop_bbox[0],
                        vop.crop_bbox[1],
                        vop.crop_bbox[0],#duplicates for now,to store adj coord
                        vop.crop_bbox[1],#duplicates for now,tostore adj coord

                        vop.red_mean,
                        vop.red_lowest,vop.red_low,vop.red_high,vop.red_highest,
                        vop.green_mean,
                        vop.green_lowest,vop.green_low,vop.green_high,vop.green_highest,
                        vop.blue_mean,
                        vop.blue_lowest,vop.blue_low,vop.blue_high,vop.blue_highest,
                        vop.voted, 
                        vop.ambiguous,
                        vop.image_filename,
                        vop.max_votes,
                        vop.overvoted
                    )
                )
            except Exception, e:
                print e
                print vop
                self.conn.rollback()
                pdb.set_trace()
                raise


        self.conn.commit()

        
    def insert(self, ballot):
        #NB all db queries are declared as strings after the method body for
        #clarity

        # new ballot approach does not include the pages attribute,
        # so if it is missing, let's just skip to the new approach.
        # ultimately the old approach can be removed.
        try:
            ballot.pages
        except AttributeError:
            insert_new(self.ballot)
        #XXX we should not have to chop it off to an arbitary and small length
        if type(ballot.pages[0]) != tuple:
            try:
                search_key = ballot.pages[0].template.barcode
            except TypeError, IndexError:
                search_key = "$".join(p.template.barcode for p in ballot.pages)
                
            name1 = ballot.pages[0].filename
            name2 = "<No such file>"
            if len(ballot.pages) > 1:
                name2 = ballot.pages[1].filename
        else:
            try:
                search_key = ballot.pages[0].template.barcode
            except TypeError, IndexError:
                search_key = "$".join(p[0].template.barcode for p in ballot.pages)
            b = ballot.pages[0]
            name1, name2 = b[0].filename, b[1].filename
        precinct = ballot.pages[0].template.precinct
        precinct = ballot.pages[0].template.party
        cur = self.conn.cursor()

        # create a record for this ballot

        cur.execute(_pg_mk, (search_key, name1, name2, precinct, party))
        sql_ret = cur.fetchall()

        try:
            ballot_id = int(sql_ret[0][0])
        except ValueError as e:
            self.conn.rollback()
            raise DatabaseError("Corrupt ballot_id")

        # write each result into our record

        for vd in ballot.results:
            try:
                cur.execute(_pg_ins, (
                        ballot_id,
                        vd.contest[:80],
                        vd.choice[:80],

                        vd.coords[0],
                        vd.coords[1],
                        vd.stats.adjusted.x,
                        vd.stats.adjusted.y, 

                        vd.stats.red.intensity,
                        vd.stats.red.darkest_fourth,
                        vd.stats.red.second_fourth,
                        vd.stats.red.third_fourth,
                        vd.stats.red.lightest_fourth,

                        vd.stats.green.intensity,
                        vd.stats.green.darkest_fourth,
                        vd.stats.green.second_fourth,
                        vd.stats.green.third_fourth,
                        vd.stats.green.lightest_fourth,

                        vd.stats.blue.intensity,
                        vd.stats.blue.darkest_fourth,
                        vd.stats.blue.second_fourth,
                        vd.stats.blue.third_fourth,
                        vd.stats.blue.lightest_fourth,

                        vd.was_voted, 
                        vd.ambiguous,
                        vd.filename,
                        vd.max_votes
                    )
                )
            except:
                self.conn.rollback()
                raise


        self.conn.commit()

_pg_mk = """INSERT INTO ballots (
            processed_at, 
            code_string, 
            file1,
            file2,
            precinct,
            party
        ) VALUES (now(), %s, %s, %s, %s, %s) RETURNING ballot_id ;"""

_pg_ins = """INSERT INTO voteops (
            ballot_id,
            contest_text,
            choice_text,

            original_x,
            original_y,
            adjusted_x,
            adjusted_y,

            red_mean_intensity,
            red_darkest_pixels,
            red_darkish_pixels,
            red_lightish_pixels,
            red_lightest_pixels,

            green_mean_intensity,
            green_darkest_pixels,
            green_darkish_pixels,
            green_lightish_pixels,
            green_lightest_pixels,

            blue_mean_intensity,
            blue_darkest_pixels,
            blue_darkish_pixels,
            blue_lightish_pixels,
            blue_lightest_pixels,

            was_voted, 
            suspicious,
            filename,
            max_votes,
            overvoted
        ) VALUES (
            %s, %s, %s,  
            %s, %s, %s, %s,
            %s, %s, %s, %s, %s, 
            %s, %s, %s, %s, %s, 
            %s, %s, %s, %s, %s, 
            %s, 
            %s, 
            %s,
            %s,
            %s
        )"""
