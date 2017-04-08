\echo '----------'  n_tevs_counts_regrouped_2 '----------'
CREATE OR REPLACE VIEW n_tevs_counts_regrouped_2 AS 


 SELECT 
 	precinct,
    sum(tevs_counts_counted) 		AS tevs_counts_counted,
    sum(tevs_counts_not_counted) 	AS tevs_counts_not_counted,
	contest_matching, 
	contest_tevs,
	choice_matching,
	choice_tevs,
    sum(tevs_tot_voteops) 			as tevs_tot_voteops,
    sum(tevs_tot_overvotes) 		as tevs_tot_overvotes
  FROM n_tevs_counts_mapped_3 
  GROUP BY precinct, contest, choice

  ;
  
-- 7283 with all right joins
-- 7534 will all left joins
-- 7539 with all full joins
-- 7765 if you take out the grouping
-- 48 rows in t2h_contest, 48 distinct values of tevs_context_text
-- 36 rows in t2h_choicde, 36 distinct values of both tevs_choice_text and hart_candidate_name 

