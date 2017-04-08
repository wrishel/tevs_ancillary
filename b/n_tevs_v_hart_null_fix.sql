
-- DROP VIEW n_tevs_v_hart_null_fix;

CREATE OR REPLACE VIEW n_tevs_v_hart_null_fix AS 
 SELECT n_tevs_v_hart_10.precinct_tevs,
    n_tevs_v_hart_10.contest_tevs,
    n_tevs_v_hart_10.choice_tevs,
    n_tevs_v_hart_10.tevs_counts_counted,
    n_tevs_v_hart_10.tevs_counts_not_counted,
    n_tevs_v_hart_10.tevs_tot_voteops,
    n_tevs_v_hart_10.tevs_tot_overvotes,
    n_tevs_v_hart_10.precinct_harts_mapped,
    n_tevs_v_hart_10.contest_harts_mapped,
    n_tevs_v_hart_10.choice_harts_mapped,
    n_tevs_v_hart_10.hart_count,
    n_tevs_v_hart_10.harts_ballots,
    n_tevs_v_hart_10.precinct_harts,
    n_tevs_v_hart_10.contest_harts,
    n_tevs_v_hart_10.choice_harts,
    n_tevs_v_hart_10.tevs_counts_counted::numeric - n_tevs_v_hart_10.hart_count::numeric AS tevs_minus_hart,
    n_tevs_v_hart_10.tevs_tot_voteops - n_tevs_v_hart_10.harts_ballots AS voteops_tev_minus_hart,
    GREATEST(abs(n_tevs_v_hart_10.tevs_counts_counted::numeric - n_tevs_v_hart_10.hart_count::numeric), abs(n_tevs_v_hart_10.tevs_tot_voteops - n_tevs_v_hart_10.harts_ballots)::numeric) AS interest_level
   FROM n_tevs_v_hart_10;

ALTER TABLE n_tevs_v_hart_null_fix
  OWNER TO tevs;