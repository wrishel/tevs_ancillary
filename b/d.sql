\echo d.sql

drop view n_margin_report_format;
create or replace view n_margin_report_format as
select 
  contest_title                   as "Contest",
	winner                          as "Winner",
  vwin                            as "Winner Votes",
	second                          as "Second",
	v2nd                            as "Second Votes",
	to_char(margin*100, '90.00%')   as "Margin"

from n_margin_report
order by contest_title
