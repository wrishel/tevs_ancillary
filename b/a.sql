select 'a.sql';

select * from harts
where precinct_name = '3MA-1' and
	contest_title ilike 'measure r'
;
\echo margin
select * from n_margin_report_pct 
where precinct_name = '3MA-1' and
	contest_title ilike 'measure r'
;
\echo harts condensed
select * from t_harts_wi_condensed_grp 
where precinct_name = '3MA-1' and
	contest_title ilike 'measure r'
;
\echo tevs mapped
select * from n_tevs_counts_mapped_5
where precinct_harts_mapped = '3MA-1' and
	contest_harts_mapped ilike 'measure r'


\quit

select distinct * from n_tevs_v_hart_10
where 
	contest_harts ilike 'measure s%'
--contest_tevs is null or choice_tevs is null
-- 26 rows without join with margins; same with; same with distinct