-- View: n_bal_voteops_not_excluded

-- DROP VIEW n_bal_voteops_not_excluded;

CREATE OR REPLACE VIEW n_bal_voteops_not_excluded AS 
 SELECT n_bal_voteops.counted_vote,
    n_bal_voteops.not_counted_vote,
    n_bal_voteops.was_voted,
    n_bal_voteops.precinct_code_string,
    n_bal_voteops.contest_text,
    n_bal_voteops.choice_text,
    n_bal_voteops.overvoted_vote,
    n_bal_voteops.suspicious,
    n_bal_voteops.max_votes,
    n_bal_voteops.ballot_page,
    n_bal_voteops.ballot_side,
    n_bal_voteops.ballot_batch,
    n_bal_voteops.file1
   FROM n_bal_voteops_1 as n_bal_voteops
  WHERE n_bal_voteops.contest_text::text <> 'NO TITLE'::text AND n_bal_voteops.choice_text::text <> 'Incorrect'::text;

ALTER TABLE n_bal_voteops_not_excluded
  OWNER TO "Wes";
