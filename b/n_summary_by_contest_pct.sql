
\echo n_summary_by_contest_pct.sql


create or replace view n_summary_by_contest_pct as
 SELECT 
    cc.contest_title,
    cc.precinct_name,
    cc.candidate_name,
    cc.sum,
    ct.all_choice
   FROM ( SELECT 
            hwcg.contest_title,
            hwcg.candidate_name,
            hwcg.precinct_name, 
            sum(hwcg.total_votes) AS sum
          FROM t_harts_wi_condensed_grp hwcg
          GROUP BY hwcg.contest_title, hwcg.precinct_name, hwcg.candidate_name) cc
     JOIN ( SELECT 
              hwcgx.contest_title,
              hwcgx.precinct_name,
              sum(hwcgx.total_votes) AS all_choice
            FROM t_harts_wi_condensed_grp hwcgx
            GROUP BY hwcgx.contest_title, hwcgx.precinct_name) ct 
     USING (contest_title, precinct_name)
  ORDER BY cc.contest_title, cc.precinct_name, cc.sum DESC;

