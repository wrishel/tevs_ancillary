
SELECT v.ballot_ID, contest_text, choice_text from voteops v
  JOIN ocrc_choice ON voteop_other = choice_text
  -- JOIN ballots b ON b.ballot_id = v.ballot_id
  WHERE ocrc_choice.interesting =TRUE

SELECT distinct v.ballot_id vb, b.ballot_id bb FROM pmitch.ballots b FULL JOIN pmitch.voteops v ON b.ballot_id = v.ballot_id
WHERE v.ballot_id is not NULL and b.ballot_id IS not NULL order by vb
SELECT distinct v.ballot_id vb, b.ballot_id bb FROM pmitch.ballots b FULL JOIN pmitch.voteops v ON b.ballot_id = v.ballot_id
WHERE v.ballot_id is  NULL or b.ballot_id IS  NULL order by vb


SELECT count(*) FROM voteops v LEFT JOIN ballots b USING (ballot_id) where b.ballot_id ISNULL

SELECT count(*) FROM voteops
