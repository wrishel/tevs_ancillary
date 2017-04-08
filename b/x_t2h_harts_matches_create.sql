-- so... why does joining with t2h_precinct add rows?
-- because t2h_precinct.hart_precinct_name is not unique
-- ... because multiple pages in ballots pertain to the same segment

-- same question for t2h_contest
--   same answer, there are multiple rows in t2h_contest for certain 
--   contests

-- why should I care?

--why does joining to candidate name reduce the numver?


-- DROP TABLE x_tevs_harts_matches_2;

-- create table x_tevs_harts_matches_2 as 

-- getting to the equivalent of the sum of votopes and votes per precinct.

-- total vallots is summed across the precinct.
-- total votees is summed across the contest/choice

-- harts has 8441 rows so any count different than that is losing something
-- from harts

-- DROP TABLE x_t2h_harts_matches_2;
-- create table x_t2h_harts_matches_2 as 
	SELECT DISTINCT
		precinct_name as precinct,
		contest_title as contest,
		candidate_name as choice,
		-- t2h_contest.hart_contest_title_pretty as contest, 
		-- t2h_choice.hart_candidate_name_pretty as choice,
--		tevs_choice_text as "tevs choice",
		total_ballots, 
		absentee_ballots + early_ballots + election_ballots as sum_ballots,
		-- absentee_ballots, 
	 -- 	early_ballots, 
		-- election_ballots, 
		total_votes, 
		early_votes+election_votes+absentee_votes as sum_votes
	 -- 	absentee_votes, 
		-- early_votes, 
		-- election_votes, 
		-- total_under_votes, 
		-- total_over_votes, 
	 -- 	absentee_under_votes, 
	 -- 	absentee_over_votes, 
		-- early_under_votes, 
		-- early_over_votes, 
		-- election_under_votes, 
		-- election_over_votes
	FROM harts
	JOIN t2h_precinct on 
		harts.precinct_name = t2h_precinct.hart_precinct_name  -- 8441 -> 8441
	FULL JOIN t2h_contest ON
	 	harts.contest_title = t2h_contest.hart_contest_title 	-- -- 8441 -> 8441
	JOIN t2h_choice ON
		harts.candidate_name = t2h_choice.hart_candidate_name 		-- 8441 -> 8441
	-- WHERE t2h_contest.hart_contest_title IS NULL
	ORDER BY precinct, contest, choice


--  precinct |                                               contest               |   choice   | total_ballots | sum_ballots | total_votes | sum_votes 
-- ----------+---------------------------------------------------------------------+------------+---------------+-------------+-------------+-----------
--  1CS-1    | MEASURE Q HUMBOLDT COUNTY CREATION OF FINANCE DEPARTMENT MEASURE.   | NO         |           630 |         630 |         281 |       281
--  1CS-1    | MEASURE Q HUMBOLDT COUNTY CREATION OF FINANCE DEPARTMENT MEASURE.   | YES        |           630 |         630 |         263 |       263


 

