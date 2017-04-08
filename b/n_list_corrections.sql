select 'n_list_corrections.sql';

-- create view n_list_corrections as
select 'choice' as field, voteop_good as correct, voteop_other as incorrect
from ocrc_choice

union

select 'contest' as field, voteop_good as correct, voteop_value as incorrect
from ocrc_contest cont
where cont.voteop_good <> cont.voteop_value

union

select 'exclude TEVS rows', '--', 'NO TITLE'

union

select 'exclude TEVS rows', '--', 'Incorrect'

union

select 'exclude HART rows', '--', 'No Candidate'

union

select 'bar code','000065', '000799'
order by field, correct
