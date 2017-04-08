-- View: n_summary_by_contest

-- DROP VIEW n_summary_by_contest;

-- CREATE OR REPLACE VIEW n_summary_by_contest AS 
 SELECT cc.contest_title,
    cc.candidate_name,
    cc.sum,
    ct.all_choice
   FROM ( SELECT 
   			    hwcg.contest_title,
            hwcg.candidate_name,
            sum(hwcg.total_votes) AS sum
           FROM t_harts_wi_condensed_grp hwcg
          GROUP BY hwcg.contest_title, hwcg.candidate_name) cc
     JOIN ( SELECT hwcgx.contest_title,
            sum(hwcgx.total_votes) AS all_choice
           FROM t_harts_wi_condensed_grp hwcgx
          GROUP BY hwcgx.contest_title) ct USING (contest_title)
  ORDER BY cc.contest_title, cc.sum DESC;

ALTER TABLE n_summary_by_contest
  OWNER TO tevs;
