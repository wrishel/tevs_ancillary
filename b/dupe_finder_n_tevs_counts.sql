\echo '----------'  dupe_finder '----------'
SELECT * FROM n_tevs_counts
JOIN
	(
	SELECT 
		count(*),
		precinct_code_string,
		contest_text,
		choice_text 
	FROM n_tevs_counts 
	GROUP BY 
		precinct_code_string,
		contest_text,
		choice_text 
	HAVING count(*) > 1
	) as dup
USING (
		precinct_code_string,
		contest_text,
		choice_text 
	) 
	;