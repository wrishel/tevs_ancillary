/*
 Although this is query #2, it is the third step in the process of
 accepting a dump file from TEVS on Ubunut. See import_from_tevs_1.sql
 for the full story.

 Wes Rishel 8/28/17
 */



ALTER SCHEMA public RENAME TO pmitch;
ALTER SCHEMA public_stash RENAME TO public;

select count(*) from public.ballots;

truncate ballots
;
insert into ballots ( -- currently ignoring subsequent columns from Mitch
  ballot_id,
  processed_at,
  code_string,
  layout_code,
  file1,
  file2,
  precinct,
  party
)
	select 
	  ballot_id,
	  processed_at,
	  code_string,
	  layout_code,
	  file1,
	  file2,
	  precinct,
	  party
 from pmitch.ballots;
;

/* fixes for specific bar-code/template/ocr errors */

-- update ballots
-- 	set (code_string, precinct_code_string) = ('20000650300096', '000065')
-- 	where file1 = '/media/OTHER/20161119/unproc/236/236700.jpg'
-- ;

/* Additions from Mitch's schema */

UPDATE ballots
     SET precinct_code_string = substring(code_string,2,6)
;     
truncate voteops
;
insert into voteops 
	select * from pmitch.voteops
;

COPY (select distinct choice_text from voteops)
TO '/Users/Wes/NotForTheCloud/choices.csv' WITH csv ;
COPY (select distinct contest_text from voteops)
TO '/Users/Wes/NotForTheCloud/contests.csv' WITH csv ;


truncate table ocrc_choice;
truncate table ocrc_contest;
truncate table harts;

/*
   1) Run octransforms.py on choices.csv
   2) edit the output to create acceptable values for each erroneous value
        (EDITING WITH EXCEL WILL NOT WORK BECAUSE IT GENERATES #NAME VALUES NO MATTER WHAT)
        include "to be fixed in the voteop_good field for values that can't be determined

   3) import into ocrc_choice
   4) get template and image file names of choices unfixed and create corrections.


   5) repeat steps 1-4 for contests.csv, input to ocrc_contest.
 */

-- COPY ocrc_choice (voteop_good, voteop_other) FROM '/Users/Wes/NotForTheCloud/OCRC_choices.csv' with csv
SELECT max(voteop_good), voteop_other, min(file1),max(code_string)
  FROM ocrc_choice o, voteops v, ballots b
  WHERE voteop_good LIKE '%to be fixed%'
  AND o.voteop_other = v.choice_text and v.ballot_id = b.ballot_id
  GROUP BY voteop_other
