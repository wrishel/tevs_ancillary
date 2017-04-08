select margin 
from n_margin
-- select * 
-- from n_bal_voteops
-- -- from ballots b join voteops v on b.ballot_id = v.ballot_id 
-- -- where (was_voted=true or suspicious=true) and overvoted=false and 
-- where contest_text = 'PROP_54' and choice_text = 'YES' AND was_voted 

-- order by contest_text, choice_text 
-- ;
-- --35122
-- \quit

select contest_text, choice_text , count(*) as votes 
-- from n_bal_voteops
from ballots b join voteops v on b.ballot_id = v.ballot_id 
where (was_voted=true or suspicious=true) and overvoted=false and 
	 contest_text in (select voteop_value from ocrc_contest where voteop_good = 'PROP_54')
-- 34952

group by contest_text, choice_text 
order by contest_text, choice_text 
;

--  contest_text | choice_text  | votes 
-- --------------+--------------+-------
--  TRIN_CC      | JACK_WEST    |   146
--  TRIN_CC      | STEVE_LADWIG |   110
--  TRIN_CC      | Write_in     |    21
-- (3 rows)

--  contest_text |  choice_text   | votes 
-- --------------+----------------+-------
--  PRES         | DONALD_J_TRUMP | 18366
-- (1 row)

