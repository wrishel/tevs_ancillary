\echo '----------'  n_bal_voteops_corrected '----------'

-- DROP VIEW n_bal_voteops_corrected;

-- CREATE OR REPLACE VIEW n_bal_voteops_corrected AS 
 SELECT 
    ocrc_contest.voteop_good,
    voteops.was_voted,
    ballots.precinct_code_string,
    COALESCE(voteops.contest_text, '---UNKNOWN---'::character varying)::character varying(80) AS xxx,
    voteops.choice_text,
    COALESCE(ocrc_contest.voteop_good, voteops.contest_text::text) AS contest_text,
    voteops.overvoted
   FROM ballots
     JOIN voteops ON ballots.ballot_id = voteops.ballot_id
     JOIN ocrc_contest ON ocrc_contest.voteop_value = voteops.contest_text::text
