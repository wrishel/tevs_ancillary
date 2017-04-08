-- View: n_harts_wi_condensed_grp_2

-- DROP VIEW n_harts_wi_condensed_grp_2;

CREATE OR REPLACE VIEW n_harts_wi_condensed_grp_2 AS 
 SELECT max(n_harts_wi_condensed.precinct_name::text) AS precinct_name,
    max(n_harts_wi_condensed.split_name::text) AS split_name,
    max(n_harts_wi_condensed.reporting_flag::text) AS reporting_flag,
    sum(n_harts_wi_condensed.update_count) AS update_count,
    max(n_harts_wi_condensed.pct_id::text) AS pct_id,
    sum(n_harts_wi_condensed.pct_seq_nbr) AS pct_seq_nbr,
    sum(n_harts_wi_condensed.reg_voters) AS reg_voters,
    NULL::real AS turn_out,  -- this is not really valid
    max(n_harts_wi_condensed.contest_id) AS contest_id,
    NULL::BIGINT AS contest_seq_nbr,
    max(n_harts_wi_condensed.contest_title::text) AS contest_title,
    max(n_harts_wi_condensed.contest_party_name::text) AS contest_party_name,
    max(n_harts_wi_condensed.selectable_options) AS selectable_options,
    max(n_harts_wi_condensed.candidate_id) AS candidate_id,
    n_harts_wi_condensed.candidate_name,
    max(n_harts_wi_condensed.candidate_type::text) AS candidate_type,
    max(n_harts_wi_condensed.cand_seq_nbr) AS cand_seq_nbr,
    max(n_harts_wi_condensed.party_code::text) AS party_code,
    max(n_harts_wi_condensed.total_ballots) AS total_ballots,
    sum(n_harts_wi_condensed.total_votes) AS total_votes,
    sum(n_harts_wi_condensed.total_under_votes) AS total_under_votes,
    sum(n_harts_wi_condensed.total_over_votes) AS total_over_votes,
    sum(n_harts_wi_condensed.absentee_ballots) AS absentee_ballots,
    sum(n_harts_wi_condensed.absentee_votes) AS absentee_votes,
    sum(n_harts_wi_condensed.absentee_under_votes) AS absentee_under_votes,
    sum(n_harts_wi_condensed.absentee_over_votes) AS absentee_over_votes,
    sum(n_harts_wi_condensed.early_ballots) AS early_ballots,
    sum(n_harts_wi_condensed.early_votes) AS early_votes,
    sum(n_harts_wi_condensed.early_under_votes) AS early_under_votes,
    sum(n_harts_wi_condensed.early_over_votes) AS early_over_votes,
    sum(n_harts_wi_condensed.election_ballots) AS election_ballots,
    sum(n_harts_wi_condensed.election_votes) AS election_votes,
    sum(n_harts_wi_condensed.election_under_votes) AS election_under_votes,
    sum(n_harts_wi_condensed.election_over_votes) AS election_over_votes
   FROM n_harts_wi_condensed
  GROUP BY n_harts_wi_condensed.precinct_name, n_harts_wi_condensed.contest_title, n_harts_wi_condensed.candidate_name;

ALTER TABLE n_harts_wi_condensed_grp
  OWNER TO tevs;
