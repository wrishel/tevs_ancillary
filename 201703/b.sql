select * from
    (select 
        array_agg(round((red_mean_intensity+green_mean_intensity+blue_mean_intensity)/3.)) intensity,
        array_agg(round((red_darkest_pixels+red_darkish_pixels+
               green_darkest_pixels+green_darkish_pixels+
               blue_darkest_pixels+blue_darkish_pixels)/3.0))   dark,

        sum(CASE
                WHEN v.was_voted 
                THEN 1
                ELSE 0
            END) as                         voted,
        sum(CASE
                WHEN v.overvoted 
                THEN 1
                ELSE 0
            END) as                         overvoted,
        sum(CASE
                WHEN v.suspicious 
                THEN 1
                ELSE 0
            END) as                         suspicions,
    file1
    from voteops v join ballots b using (ballot_id) 


(select file1 from
	(select  
		sum(CASE
	        	WHEN v.was_voted 
	        	THEN 1
	        	ELSE 0
	    	END) as 						voted,
		sum(CASE
	        	WHEN v.overvoted 
	        	THEN 1
	        	ELSE 0
	    	END) as 						overvoted,
		sum(CASE
	        	WHEN v.suspicious 
	        	THEN 1
	        	ELSE 0
	    	END) as 						suspicions,
	 file1
	from voteops v join ballots b using (ballot_id)
	group by file1, contest_text) x
where voted <> 1) troubs

