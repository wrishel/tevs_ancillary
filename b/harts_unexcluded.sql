 -- n_harts_total_votes

\echo '----------'  harts_unexcluded '----------'
select '----------' as harts_unexcluded;
CREATE OR REPLACE VIEW harts_unexcluded AS 

Select * from harts
 where id not in 
	 (SELECT id 
	 from harts
	 where 
	 	candidate_name in (
	 		'No Candidate for Race',
	 		'Unqualified Write-Ins',
			'Unresolved Write-Ins'
		) OR
		total_ballots = 0
	 )