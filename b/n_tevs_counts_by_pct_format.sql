-- create or replace view n_tevs_counts_by_pct_format AS
SELECT 
    precinct,
    sum(tevs_counts_counted) as     tevs_voteops_counted_in_pct,
    sum(tevs_counts_not_counted) as tevs_voteops_not_counted_in_pct,
    sum(tevs_counts_counted) + sum(tevs_counts_not_counted) as tevs_voteops_total_in_pct
FROM n_tevs_counts_mapped
  GROUP BY precinct;

-- ALTER TABLE n_tevs_counts_by_pct_format
--   OWNER TO tevs;