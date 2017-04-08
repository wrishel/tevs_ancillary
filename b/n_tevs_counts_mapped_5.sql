\echo '----------'  n_tevs_counts_mapped_5 '----------'
select '--------------------' as n_tevs_counts_mapped_5;

-- drop view n_tevs_counts_mapped_5;
CREATE OR REPLACE VIEW n_tevs_counts_mapped_5 AS 

SELECT 
  tc.precinct_code_string       AS precinct_tevs,
  tc.contest_text               AS contest_tevs,
  tc.choice_text                AS choice_tevs,
  tc.counted_votes::integer     AS tevs_counts_counted,
  tc.not_counted_votes::integer AS tevs_counts_not_counted,
  tc.total_voteops::integer     as tevs_tot_voteops,
  tc.overvoted::integer         as tevs_tot_overvotes,
  t2hpct.hart_precinct_name     AS precinct_harts_mapped,
  h2hcon.hart_contest_title     AS contest_harts_mapped, 
  t2hch.hart_candidate_name     AS choice_harts_mapped,
  ballot_page,
  ballot_side,
  ballot_batches

FROM n_tevs_counts_2 tc
  FULL JOIN t2h_precinct t2hpct ON tc.precinct_code_string = t2hpct.tevs_precinct_code_string
  FULL JOIN t2h_contest  t2hcon ON t2hcon.tevs_contest_text::text = tc.contest_text::text
  LEFT JOIN t2h_choice   t2hch  ON t2hch.tevs_choice_text::text = tc.choice_text::text
  LEFT JOIN h2h_contest  h2hcon ON h2hcon.hart_contest_title = t2hcon.hart_contest_title


