select * from n_bal_voteops_not_excluded
where precinct_code_string in ('000072', '000078', '000015', '000047', '000045', '000042', '000048', '000124', '000110')
order by contest_text
\quit
select * from t2h_precinct
where hart_precinct_name in ('2SH-3', '3MA-1', '2SHF1', '3FW', '1FS-4', '2SHR1', '5KTS3', '5PA-3', '2SH-7')

\quit


select distinct
  precinct_tevs,
  contest_tevs,
  choice_tevs,
  precinct_harts--,
  -- LEFT(x.contest_harts,15) contest_harts,
  -- left(x.choice_harts, 15) choice_harts
from 

  (SELECT 
  precinct_tevs,
  precinct_harts,
      contest_tevs,
      choice_tevs,
     contest_harts,
     choice_harts,
    hart_count       as hart,
     tevs_counts_counted  as tevs,
     harts_ballots      as hart_ops,
     tevs_tot_voteops     as tevs_ops,
     tevs_minus_hart    as tevs_less_hart,
     voteops_tev_minus_hart ops_tevs_less_hart
    
  FROM n_tevs_v_hart_10) X
where contest_harts ilike 'measure s%' and precinct_tevs is null
-- where contest_tevs is null or choice_tevs is null
-- order by precinct_harts, contest_harts, choice_harts
--  group by contest_tevs, choice_tevs
-- order by ops_tevs_less_hart
-- aggregated across the county
-- nothing in tevs for contest and choice, 
-- multiple contests and choices from harts
-- | | PROPOSITION 66 | YES | MEASURE R HUMBO | NO | 2993 | 0 | 6728 | 0 | -2993 | -6728 | -100.00%
