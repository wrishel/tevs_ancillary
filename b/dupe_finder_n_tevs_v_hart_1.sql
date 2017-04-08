\echo '----------'  dupe_finder '----------'
SELECT * FROM n_tevs_v_hart_1
JOIN
	(
	SELECT 
		count(*),
		precinct_tevs,
		precinct_harts,
		contest,
		choice 
	FROM n_tevs_v_hart_1 
	GROUP BY 
		precinct_tevs,
		precinct_harts,
		contest,
		choice 
	HAVING count(*) > 1
	) as dup
USING (
		precinct_tevs,
		precinct_harts,
		contest,
		choice
	) 
	;