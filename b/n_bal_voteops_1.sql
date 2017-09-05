-- View: n_bal_voteops

-- DROP VIEW n_bal_voteops;

CREATE OR REPLACE VIEW n_bal_voteops_1 AS 
 SELECT
        CASE
            WHEN (v.was_voted OR v.suspicious) AND NOT v.overvoted THEN 1
            ELSE NULL::integer
        END AS counted_vote,
        CASE
            WHEN (v.was_voted OR v.suspicious) AND NOT v.overvoted THEN NULL::integer
            ELSE 1
        END AS not_counted_vote,
    v.was_voted,
    b.precinct_code_string,
    COALESCE(ocrc.voteop_good, v.contest_text::text)::character varying(80) AS contest_text,
    COALESCE(ocrch.voteop_good, v.choice_text::text)::character varying(80) AS choice_text,
        CASE
            WHEN v.overvoted THEN 1
            ELSE NULL::integer
        END AS overvoted_vote,
    v.suspicious,
    v.max_votes,
    "left"(b.code_string::text, 1) AS ballot_page,
    substr(b.code_string::text, 9, 1) AS ballot_side,
    (string_to_array(b.file1::text, '/'::text))[6] AS ballot_batch,
    file1
   FROM ballots b
     JOIN voteops v ON b.ballot_id = v.ballot_id
     FULL JOIN ocrc_contest ocrc ON ocrc.voteop_value = v.contest_text::text
     FULL JOIN ocrc_choice ocrch ON ocrch.voteop_other = v.choice_text::text;

ALTER TABLE n_bal_voteops
  OWNER TO "Wes";
