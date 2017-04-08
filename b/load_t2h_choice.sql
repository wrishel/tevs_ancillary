TRUNCATE t2h_choice;

COPY t2h_choice
(
	hart_candidate_name,
	tevs_choice_text
)
FROM '/Users/Wes/Dropbox/Programming/ElectionTransparency/h2t_choice.csv' DELIMITER ',' CSV HEADER;
