-- View: n_tevs_counts_2

-- DROP VIEW n_tevs_counts_2;

CREATE OR REPLACE VIEW n_tevs_counts_2 AS 
SELECT 
    sum(counted_vote)               AS counted_votes,
    sum(not_counted_vote)           AS not_counted_votes,
    precinct_code_string,
    contest_text,
    choice_text,
    SUM(MAX_VOTES)                  as total_voteops,
    sum(overvoted_vote)             as overvoted,
    max(ballot_page)                as ballot_page,
    max(ballot_side)                as ballot_side,
    array_agg(ballot_batch)			as ballot_batches
FROM n_bal_voteops_not_excluded
GROUP BY precinct_code_string, contest_text, choice_text
