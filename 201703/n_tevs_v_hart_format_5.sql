-- View: n_tevs_v_hart_format_5

DROP VIEW n_tevs_v_hart_format_5;

CREATE OR REPLACE VIEW n_tevs_v_hart_format_5 AS 
 SELECT tvh.precinct_tevs AS "Precinct TEVS",
    tvh.ballot_page AS "Ballot Page",
    tvh.ballot_side AS "ballot Side",
    -- array_to_string(bb.ballot_batches, ' '::text) AS "Ballot Batches",
    -- tvh.contest_tevs AS "Contest TEVS",
    -- tvh.choice_tevs AS "Choice TEVS",
    tvh.tevs_counts_counted AS "TEVS Voteops Marked",
    tvh.tevs_tot_voteops AS "TEVS Total Voteops",
    tvh.tevs_counts_not_counted AS "TEVS Voteops not Marked",
    tvh.tevs_tot_overvotes AS "TEVS Over Votes",
    '~  '::text || tvh.precinct_harts::text AS "Precinct HART",
    "left"(tvh.contest_harts::text, 23) AS "Contest HART",
    "left"(tvh.choice_harts::text, 21) AS "Choice HART",
    tvh.hart_count AS "HART Count",
    tvh.harts_ballots AS "HART Ballots",
    tvh.tevs_minus_hart AS "Votes Counted TEVS Minus HART",
    tvh.voteops_tev_minus_hart AS "Total Voteops TEVS Minus HART",
    abs(tvh.tevs_minus_hart) AS "ABS Votes Counted TEVS Minus HART",
    abs(tvh.voteops_tev_minus_hart) AS "ABS Total Voteops TEVS Minus HART",
    tvh.margin AS "Margin",
        CASE
            WHEN tvh.margin = 0::double precision THEN '--'::text
            ELSE to_char(abs(tvh.tevs_minus_hart)::double precision / tvh.margin * 100::double precision, '990.00%'::text)
        END AS "Error Pct",
    (((COALESCE(tvh.precinct_harts, tvh.precinct_harts_mapped)::text || '.'::text) || COALESCE(tvh.contest_harts, tvh.contest_harts_mapped)::text) || '.'::text) || COALESCE(tvh.choice_harts, tvh.choice_harts_mapped)::text AS "Sort Key"
   FROM n_tevs_v_hart_10 tvh
     JOIN n_ballot_batches_1 bb ON bb.precinct_code_string = tvh.precinct_tevs AND bb.contest_text::text = tvh.contest_tevs::text AND bb.choice_text::text = tvh.choice_tevs::text
  ORDER BY COALESCE(tvh.precinct_harts, tvh.precinct_harts_mapped), COALESCE(tvh.contest_harts, tvh.contest_harts_mapped), COALESCE(tvh.choice_harts, tvh.choice_harts_mapped);

ALTER TABLE n_tevs_v_hart_format_5
  OWNER TO tevs;
