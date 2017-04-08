\echo '----------'  n_bal_voteops_not_excluded  '----------'
select '----------' as n_bal_voteops_not_excluded ;


CREATE OR REPLACE VIEW n_bal_voteops_not_excluded AS 
select * from n_bal_voteops
where 
	contest_text <> 'NO TITLE' and
	choice_text <> 'Incorrect'
