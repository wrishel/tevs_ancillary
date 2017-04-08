-- View: n_tevs_voteops_per_precinct

-- view n_tevs_v_hart depends on view n_tevs_voteops_per_precinct

-- DROP VIEW n_tevs_voteops_per_precinct;

CREATE OR REPLACE VIEW n_tevs_voteops_per_precinct AS 
 SELECT count(*) AS votops_per_precinct,
    t2h_precinct_page.hart_precinct_name
   FROM ballots
     JOIN voteops ON ballots.ballot_id = voteops.ballot_id
     JOIN t2h_precinct_page ON t2h_precinct_page.tevs_code_string_precinct::text = ballots.precinct_code_string::text
  GROUP BY t2h_precinct_page.hart_precinct_name;

ALTER TABLE n_tevs_voteops_per_precinct
  OWNER TO tevs;
