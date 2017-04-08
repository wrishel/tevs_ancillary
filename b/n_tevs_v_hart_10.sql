-- drop view n_tevs_v_hart_10;
\echo '----------'  n_tevs_v_hart_10 '----------'
select '----------' as n_tevs_v_hart_10;
CREATE OR REPLACE VIEW n_tevs_v_hart_10 AS 
SELECT 
  	tcm.precinct_tevs  as precinct_tevs,
  	tcm.contest_tevs::varchar(80)                     as contest_tevs,
  	tcm.choice_tevs::varchar(80)                      as choice_tevs,
  	coalesce(tcm.tevs_counts_counted, 0)              as tevs_counts_counted,
  	coalesce(tcm.tevs_counts_not_counted, 0)          as tevs_counts_not_counted,
  	coalesce(tcm.tevs_tot_voteops, 0)                 as tevs_tot_voteops,
  	coalesce(tcm.tevs_tot_overvotes, 0)               as tevs_tot_overvotes,
  	tcm.precinct_harts_mapped, 
  	tcm.contest_harts_mapped,  
  	tcm.choice_harts_mapped, 
 
    coalesce(hunx.total_votes::integer, 0)            AS hart_count,
    coalesce(hunx.total_ballots, 0)::integer          as harts_ballots,
  
      
    hunx.precinct_name::varchar                       as precinct_harts,
    hunx.contest_title::varchar                       as contest_harts,
    hunx.candidate_name::varchar                      as choice_harts,
    coalesce(tcm.tevs_counts_counted::numeric,0) -  
      coalesce(hunx.total_votes::integer, 0)::integer AS tevs_minus_hart,
    coalesce(tcm.tevs_tot_voteops, 0) - 
      coalesce(hunx.total_ballots, 0)::integer        AS voteops_tev_minus_hart,
    tcm.ballot_page,
    tcm.ballot_side,
    m.margin_votes::real                              as margin,
    tcm.ballot_batches
  
   FROM n_tevs_counts_mapped_5 as tcm
   FULL JOIN t_harts_wi_condensed_grp as hunx ON 
     tcm.precinct_harts_mapped = hunx.precinct_name AND  
     tcm.contest_harts_mapped = hunx.contest_title AND  
     tcm.choice_harts_mapped = hunx.candidate_name
   LEFT JOIN n_margin_report as m ON
      m.contest_title = hunx.contest_title

