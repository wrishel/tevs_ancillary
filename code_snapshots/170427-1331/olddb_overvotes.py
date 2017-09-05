import db
import sys

def process_overvotes(dbc):
	try:
            retval = dbc.query_no_return_value("drop table overvotes;")
        except Exception, e:
            print e

        try:
            retval = dbc.query_no_return_value("drop table overvote_ids;")
        except Exception, e:
            print e

        try:
            retval = dbc.query_no_return_value("drop table overvote_values;")
        except Exception, e:
            print e

        try:
		retval = dbc.query_no_return_value("drop table overvote_diffs;")
        except Exception, e:
            print e

        try:
		
            retval = dbc.query_no_return_value("""
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
        try:
            retval = dbc.query_no_return_value("""
select v.voteop_id 
       into overvote_ids 
       from overvotes o 
       join voteops v 
       on o.contest_text_standardized_id = v.contest_text_standardized_id 
       join ocr_variants ocr on v.contest_text_standardized_id = ocr.id
       and o.filename = v.filename 
       where o.votes > ocr.max_votes_in_contest;
""")
        except Exception, e:
            print e
            raise

        try:
            retval = dbc.query_no_return_value("""
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

        try:
            retval = dbc.query_no_return_value("""
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
            retval = dbc.query_no_return_value("""
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
            retval = dbc.query_no_return_value("""
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

        try:
            retval = dbc.query_no_return_value("""
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


if __name__ == "__main__":
	if len(sys.argv)!=2:
		print "Usage: python db_overvotes.py database username"
		return
        dbc = db.PostgresDB(sys.argv[1], sys.argv[2])
	process_overvotes(dbc)
