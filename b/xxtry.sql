SELECT 
  voteops.voteop_id, 
  voteops.ballot_id, 
  voteops.suspicious, 
  voteops.overvoted, 
  voteops.contest_text_id, 
  voteops.contest_text_standardized_id, 
  voteops.choice_text_id, 
  voteops.choice_text_standardized_id, 
  voteops.contest_text, 
  voteops.choice_text
FROM 
  public.voteops
WHERE 
  voteops.contest_text = 'MEAS_Q' AND 
  voteops.choice_text_id = 'YES';
