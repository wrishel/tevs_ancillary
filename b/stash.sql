\echo '----------'  n_harts_WI_condensed_grp '----------'
select '----------' as n_harts_WI_condensed_grp;

CREATE OR REPLACE VIEW n_harts_WI_condensed_grp AS
select 
  max(precinct_name) as precinct_name, 
  max(split_name) as split_name, 
  max(reporting_flag) as reporting_flag, 
  sum(update_count) as update_count, 
  max(pct_id) as pct_id, 
  sum(pct_seq_nbr) as pct_seq_nbr, 
  sum(reg_voters) as reg_voters, 
  sum(turn_out) as turn_out, 
  max(contest_id) as contest_id, 
  sum(contest_seq_nbr) as contest_seq_nbr, 
  max(contest_title) as contest_title, 
  max(contest_party_name) as contest_party_name, 
  max(selectable_options) as selectable_options, 
  max(candidate_id) as candidate_id, 
  candidate_name,
  max(candidate_type) as candidate_type, 
  max(cand_seq_nbr) as cand_seq_nbr, 
  max(party_code) as party_code, 
  sum(total_ballots) as total_ballots, 
  sum(total_votes) as total_votes, 
  sum(total_under_votes) as total_under_votes, 
  sum(total_over_votes) as total_over_votes, 
  sum(absentee_ballots) as absentee_ballots, 
  sum(absentee_votes) as absentee_votes, 
  sum(absentee_under_votes) as absentee_under_votes, 
  sum(absentee_over_votes) as absentee_over_votes, 
  sum(early_ballots) as early_ballots, 
  sum(early_votes) as early_votes, 
  sum(early_under_votes) as early_under_votes, 
  sum(early_over_votes) as early_over_votes, 
  sum(election_ballots) as election_ballots, 
  sum(election_votes) as election_votes, 
  sum(election_under_votes) as election_under_votes, 
  sum(election_over_votes) as election_over_votes

from n_harts_WI_condensed
group by precinct_name, contest_title, candidate_name
