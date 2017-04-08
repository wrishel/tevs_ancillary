DROP VIEW n_harts_ballot_by_precinct;
CREATE OR REPLACE VIEW n_harts_ballot_by_precinct AS 
SELECT 
	precinct_name,
	choices_across_contests_in_precinct,
	total_votes_in_precinct,
	total_ballots_in_precinct,
	choices_across_contests_in_precinct * total_ballots_in_precinct as voteops_in_precinct
FROM 
	(SELECT harts.precinct_name,
	    count(*) AS choices_across_contests_in_precinct,
	    max(total_ballots) as total_ballots_in_precinct,
	    sum(total_votes) as total_votes_in_precinct
	  FROM harts
	  GROUP BY harts.precinct_name) pct
  ORDER BY pct.precinct_name