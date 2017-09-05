select 
    round((red_mean_intensity+green_mean_intensity+blue_mean_intensity)/3.) intensity,
    round((red_darkest_pixels+red_darkish_pixels+
               green_darkest_pixels+green_darkish_pixels+
               blue_darkest_pixels+blue_darkish_pixels)/3.0)    dark,
               -- contest_text,
               choice_text,
               was_voted,
               overvoted,
               file1
from ballots join voteops using (ballot_id)
where ballot_id in
(select ballot_id from 
    (select voted, ballot_id from
       (select 
            sum(CASE
                    WHEN v.was_voted 
                    THEN 1
                    ELSE 0
                END) as                         voted,
        ballot_id
        from voteops v join ballots b using (ballot_id)
        group by ballot_id, contest_text) x   
    where voted <> 1) troubles)
order by file1, overvoted, choice_text

