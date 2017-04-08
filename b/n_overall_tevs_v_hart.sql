select 'n_overall_tevs_v_hart';

-- create or replace view n_overall_tevs_v_hart as
SELECT 
  	contest_tevs,
  	choice_tevs,
  	max(left(contest_harts, 15)),
  	max(left(choice_harts,10)),
  	min(left(contest_harts, 15)),
  	min(left(choice_harts,10)),
    sum(hart_count) 			as hart,
  	sum(tevs_counts_counted) 	as tevs,
    sum(harts_ballots) 			as hart_ops,
  	sum(tevs_tot_voteops) 		as tevs_ops,
    sum(tevs_minus_hart) 		as tevs_less_hart,
    sum(voteops_tev_minus_hart) ops_tevs_less_hart,
    case 
    	when sum(hart_count) = 0
    	then '9999   '::text
    	else to_char(sum(tevs_minus_hart)/sum(hart_count)*100, '990.00%')
    	end as "tevs less hart/hart_ops"
  
FROM n_tevs_v_hart_10
group by contest_tevs, choice_tevs
-- order by ops_tevs_less_hart
-- aggregated across the county
-- nothing in tevs for contest and choice, 
-- multiple contests and choices from harts
-- | | PROPOSITION 66 | YES | MEASURE R HUMBO | NO | 2993 | 0 | 6728 | 0 | -2993 | -6728 | -100.00%
