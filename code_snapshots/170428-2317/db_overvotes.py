import sys
import psycopg2

#using partition
# select ballot_id,
# substring(choice_text,1,10),
# substring(contest_text,1,10),
# avg(red_mean_intensity) over (partition by ballot_id, was_voted, contest_text) as avred,
# max(red_mean_intensity) over (partition by ballot_id, was_voted, contest_text) as maxred
# from voteops;



def process_overvotes(conn):
    """send the necessary series of commands to the database, print progress"""
    cur = conn.cursor()
    try:
        cur.execute("drop table if exists overvotes cascade;")
    except Exception, e:
        conn.rollback()
        print e

    try:
        cur.execute("drop table if exists overvote_ids cascade;")
    except Exception, e:
        conn.rollback()
        print e

    try:
        cur.execute("drop table if exists overvote_values cascade;")
    except Exception, e:
        conn.rollback()
        print e

    try:
        cur.execute("drop table if exists overvote_diffs cascade;")
    except Exception, e:
        conn.rollback()
        print e

    print "Step 1 of 5: obtaining votes per contest per ballot"
    try:
        cur.execute("""
select count(*) as votes, contest_text_standardized_id, filename 
       into overvotes 
       from voteops 
       where was_voted 
       group by contest_text_standardized_id, filename;
""")
    except Exception, e:
        print e
        raise

	# do this for every contest_text variant, 
	# in ocr_variants, using the max_votes_in_contest
	# as the
    print "Step 2 of 5: identifying votes that might be overvoted"
    try:
        cur.execute("""
select v.voteop_id 
       into overvote_ids 
       from overvotes o 
       join voteops v 
       on o.contest_text_standardized_id = v.contest_text_standardized_id 
       join ocr_variants ocr on v.contest_text_standardized_id = ocr.id
       and o.filename = v.filename 
       where o.votes > ocr.max_votes_in_contest;
""")
    except psycopg2.ProgrammingError, e:
        print "You must merge first."
        return

    except Exception, e:
        print e
        raise

    print "Step 3 of 5: getting darkness of votes that might be overvoted"
    try:
        cur.execute("""
select v.voteop_id, 
       substring(v.filename,28,15) as filename ,
       substring(v.contest_text,1,30) as contest,
       substring(v.choice_text,1,30) as choice, 
       v.red_darkest_pixels as darkest, 
       v.red_mean_intensity as intensity 
       into overvote_values 
       from overvote_ids o join voteops v 
       on o.voteop_id = v.voteop_id where was_voted;
""")
    except Exception, e:
        print e
        raise

    print "Step 4 of 5: accepting darker if darkness varies substantially"
    try:
        cur.execute("""
select a.*, b.voteop_id as b_voteop_id, 
       (a.intensity - b.intensity) as intensity_a_less_intensity_b 
       into overvote_diffs 
       from overvote_values a join overvote_values b 
       on a.contest = b.contest and a.filename=b.filename and a.choice != b.choice; 
""")
    except Exception, e:
        print e
        raise

    # if one vote's intensity is 30 points below that of another,
    # give the vote to the darker, but leave suspicious
    try:
        cur.execute("""
update voteops 
       set was_voted = False, overvoted=False, suspicious=True 
       where voteop_id in 
       (select b_voteop_id 
       	       from overvote_diffs 
	       where intensity_a_less_intensity_b < -30);

""")
    except Exception, e:
        print e
        raise

    try:
        cur.execute("""
update voteops 
       set was_voted = False, overvoted=False,
       suspicious = True
       where voteop_id in 
       (select voteop_id 
       	       from overvote_diffs 
	       where intensity_a_less_intensity_b > 30);

""")
    except Exception, e:
        print e
        raise

    print "Step 5 of 5: flagging overvotes without large darkness difference"
    try:
        cur.execute("""
update voteops 
       set was_voted = True, 
       suspicious = True,
       overvoted = True,
       where voteop_id in 
       (select voteop_id 
       	       from overvote_diffs 
	       where (intensity_a_less_intensity_b <= 30) 
               and (intensity_a_less_intensity_b >= -30)
);

""")
    except Exception, e:
        print e
        raise

    print "Overvote processing complete."

if __name__ == "__main__":
    if len(sys.argv)!=3:
        print sys.argv
        print "Usage: python db_overvotes.py database username"
        sys.exit(0)
    conn = psycopg2.connect(database=sys.argv[1], user=sys.argv[2], port=5433)
    process_overvotes(conn)
    sys.exit(0)
