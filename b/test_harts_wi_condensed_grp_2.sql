\echo test_harts_wi_condensed_grp_2.sql

-- insert some test data into this view to cover the case where there is only
-- one choice for a race

create view test_harts_wi_condensed_grp_2 as
select precinct_name ,
 split_name ,
 reporting_flag ,
 update_count ,
 pct_id ,
 pct_seq_nbr ,
 reg_voters ,
 turn_out ,
 contest_id ,
 contest_seq_nbr ,
 contest_title ,
 contest_party_name ,
 selectable_options ,
 candidate_id ,
 candidate_name ,
 candidate_type ,
 cand_seq_nbr ,
 party_code ,
 total_ballots ,
 total_votes ,
 total_under_votes ,
 total_over_votes ,
 absentee_ballots ,
 absentee_votes ,
 absentee_under_votes ,
 absentee_over_votes ,
 early_ballots ,
 early_votes ,
 early_under_votes ,
 early_over_votes ,
 election_ballots ,
 election_votes ,
 election_under_votes ,
 election_over_votes 
from xtestdata_n_harts_wi_condensed_grp_1
union
select * from n_harts_wi_condensed_grp_2
