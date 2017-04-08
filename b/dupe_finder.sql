\echo '----------'  dupe_finder '----------'
select 
			count,
			* 

FROM
	(SELECT * FROM t2h_precinct
	JOIN
		(
		SELECT 
			count(*),
			hart_precinct_name
		FROM t2h_precinct 
		GROUP BY 
			hart_precinct_name
		) counter
	USING (
			hart_precinct_name
		) 
		
	ORDER BY 
			hart_precinct_name
	) alldup 
WHERE count > 1
;