

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

select distinct choice_text from voteops;
select distinct contest_text from voteops;
truncate table ocrc_choice;
truncate table ocrc_contest;
truncate table harts;

