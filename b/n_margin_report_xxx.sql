\echo n_margin_report.sql

-- drop view n_margin_report;
-- create or replace view n_margin_report as
select
  contest_title,
  winner,
  second,
  vwin,
  v2nd,
  margin,
  rn
from
  (select * from 
    (select 
      x.contest_title as contest_title,
      left(first_value(candidate_name) over w, 15)  as winner,
      left(nth_value(candidate_name, 2) over w, 15) as second,
      first_value(sum) over w                       as vwin,
      nth_value(sum, 2) over w                      as v2nd,
      (((first_value(sum) over w) - 
        (nth_value(sum, 2) over w)) / all_choice)
                                                    as margin,
      row_number() over w                           as rn,
      ((first_value(sum) over w) - 
        (nth_value(sum, 2) over w))                 as margin_votes
    from n_summary_by_contest x
    window w as (PARTITION by contest_title order by contest_title, sum desc) 

    ) wind_select
  where rn = 2) row_select
union 
  select 
      contest_title,
      winner,
      second,
      vwin,
      v2nd,
      margin ,
      rn
  from
  ( select 
      contest_title,
      max(candidate_name)                       as winner,
      '(No second place)'::text                 as second,
      sum(sum)                                  as vwin,
      0                                         as v2nd,
      0.0::real                                 as margin,
      1                                         as rn,
      0                                         as margin_votes
    from n_summary_by_contest 
    group by contest_title) n  
  where num_candidates_in_contest =1
order by contest_title 
