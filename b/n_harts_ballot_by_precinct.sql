CREATE OR REPLACE VIEW n_harts_ballot_by_precinct AS 
 SELECT pct.precinct_name,
    pct.choices_across_contests_in_precinct,
    pct.total_votes_in_precinct,
    pct.total_ballots_in_precinct,
    pct.choices_across_contests_in_precinct * pct.total_ballots_in_precinct AS voteops_in_precinct
   FROM ( SELECT h.precinct_name,
            count(*) AS choices_across_contests_in_precinct,
            max(h.total_ballots) AS total_ballots_in_precinct,
            sum(h.total_votes) AS total_votes_in_precinct
           FROM harts_unexcluded as h
          GROUP BY h.precinct_name) pct
