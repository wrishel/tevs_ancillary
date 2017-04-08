select 'h.sql';

-- create view cx_pres as
-- select contest_tevs, choice_tevs, tevs_counts_counted, precinct_harts
-- from n_tevs_v_hart_10
-- where contest_tevs = 'PRES'

-- \quit

/*
    what i think I want is colums for 
      contest 1
      choice 1
      contest 2
      choice 2
      pct 1
      pct 1
      correlation between precincts on contest1/choice1 vs contest2/choice2
*/

select * from 
  (select 
    counts1.pct,
    contest1,
    counts1.choice_tevs as choice1,
    count1,
    contest2,
    counts2.choice_tevs as choice2,
    count2
  from (select 'PRES'::text as contest1, 'PROP_62'::text as contest2) as params
  join (
        select contest_tevs, choice_tevs, precinct_harts as pct, tevs_counts_counted as count1
        from n_tevs_v_hart_10 ntvh
       ) counts1
  on  counts1.contest_tevs = params.contest1
  join (
        select contest_tevs, choice_tevs, precinct_harts as pct, tevs_counts_counted as count2
        from n_tevs_v_hart_10 ntvh
       ) counts2
  on  counts2.contest_tevs = params.contest2 and
      counts2.pct = counts1.pct ) x
where pct is not null -- unresolved TEVS entries
order by contest1, contest2, choice1, choice2, pct

\quit

select contest_tevs, choice_tevs, tevs_counts_counted, pnames.pct, pnames.pct2
from cx_pres
join (
    select distinct 
      t1.precinct_name as pct,
      t2.precinct_name as pct2
    from t_harts_wi_condensed_grp t1
    join 
    (select distinct precinct_name 
    from t_harts_wi_condensed_grp) t2
    on t1.precinct_name <> t2.precinct_name
  ) pnames
on cx_pres.precinct_harts = pnames.pct OR
   cx_pres.precinct_harts = pnames.pct2
order by pnames.pct, pnames.pct2
