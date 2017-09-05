-- CREATE OR REPLACE VIEW n_tevs_v_hart_10 AS 
 SELECT distinct tcm.precinct_tevs,
    tcm.contest_tevs,
    tcm.choice_tevs,
    tcm.precinct_harts_mapped,
    tcm.contest_harts_mapped,
    tcm.choice_harts_mapped,
    hunx.precinct_name::character varying AS precinct_harts,
    hunx.contest_title::character varying AS contest_harts,
    hunx.candidate_name AS choice_harts
   FROM n_tevs_counts_mapped_5 tcm
     FULL JOIN t_harts_wi_condensed_grp hunx ON 
        tcm.precinct_harts_mapped::text = hunx.precinct_name AND 
        tcm.contest_harts_mapped::text = hunx.contest_title AND 
        tcm.choice_harts_mapped::text = hunx.candidate_name::text
     