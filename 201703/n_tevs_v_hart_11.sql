--CREATE OR REPLACE VIEW n_tevs_v_hart_10 AS 
 SELECT tcm.precinct_tevs,
    tcm.contest_tevs,
    tcm.choice_tevs,
    COALESCE(tcm.tevs_counts_counted, 0) AS tevs_counts_counted,
    COALESCE(tcm.tevs_counts_not_counted, 0) AS tevs_counts_not_counted,
    COALESCE(tcm.tevs_tot_voteops, 0) AS tevs_tot_voteops,
    COALESCE(tcm.tevs_tot_overvotes, 0) AS tevs_tot_overvotes,
    tcm.precinct_harts_mapped,
    tcm.contest_harts_mapped,
    tcm.choice_harts_mapped,
    COALESCE(hunx.total_votes::integer, 0) AS hart_count,
    COALESCE(hunx.total_ballots, 0) AS harts_ballots,
    hunx.precinct_name::character varying AS precinct_harts,
    hunx.contest_title::character varying AS contest_harts,
    hunx.candidate_name AS choice_harts,
    COALESCE(tcm.tevs_counts_counted::numeric, 0::numeric) - COALESCE(hunx.total_votes::integer, 0)::numeric AS tevs_minus_hart,
    COALESCE(tcm.tevs_tot_voteops, 0) - COALESCE(hunx.total_ballots, 0) AS voteops_tev_minus_hart,
    tcm.ballot_page,
    tcm.ballot_side,
    m.margin_votes::real AS margin,
    tcm.ballot_batches
   FROM n_tevs_counts_mapped_5 tcm
     LEFT JOIN t_harts_wi_condensed_grp hunx ON tcm.precinct_harts_mapped::text = hunx.precinct_name AND tcm.contest_harts_mapped::text = hunx.contest_title AND tcm.choice_harts_mapped::text = hunx.candidate_name::text
     LEFT JOIN n_margin_report m ON m.contest_title = hunx.contest_title;