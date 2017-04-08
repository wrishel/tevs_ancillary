\echo '----------'  n_harts_WI_condensed '----------'
select '----------' as n_harts_WI_condensed;

CREATE OR REPLACE VIEW n_harts_WI_condensed AS
select 
  precinct_name, 
  split_name, 
  reporting_flag, 
  update_count, 
  pct_id, 
  pct_seq_nbr, 
  reg_voters, 
  turn_out, 
  contest_id, 
  contest_seq_nbr, 
  CASE
    WHEN contest_title like 'EUREKA CITY COUNCILMEMBER%'
    THEN 'EUREKA CITY COUNCILMEMBER'
    ELSE contest_title
  END                              as contest_title, 
  contest_party_name, 
  selectable_options, 
  candidate_id, 
  CASE 
    WHEN candidate_type in ('W', 'R', 'U')
    THEN 'Write_in'
    ELSE candidate_name
    END 											     as candidate_name,
  candidate_type, 
  cand_seq_nbr, 
  party_code, 
  total_ballots * selectable_options as total_ballots, 
  total_votes, 
  total_under_votes, 
  total_over_votes, 
  absentee_ballots, 
  absentee_votes, 
  absentee_under_votes, 
  absentee_over_votes, 
  early_ballots, 
  early_votes, 
  early_under_votes, 
  early_over_votes, 
  election_ballots, 
  election_votes, 
  election_under_votes, 
  election_over_votes
from n_harts_unexcluded
