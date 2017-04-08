DROP TABLE t2h_choice;

CREATE TABLE t2h_choice -- HART contest precinct vote-opportunity choice
(
	id					serial NOT NULL,
	hart_candidate_name	character varying,
	tevs_choice_text	character varying,
	CONSTRAINT t2hc_pkey PRIMARY KEY (id)
);
