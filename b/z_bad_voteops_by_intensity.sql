select 
    round((red_mean_intensity+green_mean_intensity+blue_mean_intensity)/3.) intensity,
    round((red_darkest_pixels+red_darkish_pixels+
               green_darkest_pixels+green_darkish_pixels+
               blue_darkest_pixels+blue_darkish_pixels)/3.0)    dark,
    case when was_voted or overvoted then 1 else 0 end as       hit,
    file1
from ballots join voteops using (ballot_id)
