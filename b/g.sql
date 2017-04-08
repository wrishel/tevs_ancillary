
\echo g.sql

 select
  contest_title,
  precinct_name,
  winner,
  second,
  vwin,
  v2nd,
  margin,
  rn
from
  (select * from 
    (select 
      left(x.contest_title, 25)                     as contest_title,
                                                       precinct_name,
      left(first_value(candidate_name) over w, 15)  as winner,
      left(nth_value(candidate_name, 2) over w, 15) as second,
      first_value(sum) over w                       as vwin,
      nth_value(sum, 2) over w                      as v2nd,
      (((first_value(sum) over w) - 
        (nth_value(sum, 2) over w)) / all_choice)
                                                    as margin,
      row_number() over w                           as rn
    from n_summary_by_contest_pct x
    window w as (
      PARTITION by contest_title, precinct_name 
      order by contest_title, precinct_name, sum desc) 

    ) wind_select
  where rn = 2) row_select
union 
  select 
      contest_title,
      precinct_name,
      winner,
      second,
      vwin,
      v2nd,
      margin ,
      rn
  from
  ( select 
      contest_title,
      precinct_name,
      max(candidate_name) as winner,
      '(No second place)'::text as second,
      sum(sum) as vwin,
      0 as v2nd,
      0.0::real as margin,
      1 as rn,
      count(*) num_candidates_in_contest
    from n_summary_by_contest_pct 
    group by contest_title, precinct_name) n  
  where num_candidates_in_contest =1
order by contest_title, precinct_name


