
\echo '----------'  n_harts_unexcluded '----------'
select '----------' as n_harts_unexcluded;
CREATE OR REPLACE VIEW n_harts_unexcluded AS 

Select * from harts
where 
 	candidate_name not in ('No Candidate for Race') and
	total_ballots <> 0
