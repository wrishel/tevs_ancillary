-- View: n_tevs_counts_by_pct

-- DROP VIEW n_tevs_counts_by_pct;

CREATE OR REPLACE VIEW n_tevs_counts_by_pct AS 
 SELECT tcm.precinct_harts_mapped 							as precinct,
    sum(tcm.tevs_counts_counted)::numeric 					AS tevs_voteops_counted_in_pct,
    sum(tcm.tevs_counts_not_counted)::numeric 				AS tevs_voteops_not_counted_in_pct,
    (sum(tcm.tevs_counts_counted) + sum(tcm.tevs_counts_not_counted))::numeric 
    														AS tevs_voteops_total_in_pct
   FROM n_tevs_counts_mapped_5 tcm
  GROUP BY tcm.precinct_harts_mapped;

ALTER TABLE n_tevs_counts_by_pct
  OWNER TO tevs;
