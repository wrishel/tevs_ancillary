DTD = """<!DOCTYPE BallotSide [
	  <!ELEMENT Landmarks (#PCDATA) >
	  <!ELEMENT Vote (#PCDATA)>
	  <!ELEMENT Box (Vote*)>
	  <!ELEMENT BallotSide (Landmarks, Box*)>
	  <!ATTLIST BallotSide layout  CDATA #IMPLIED
		    precinct  CDATA #IMPLIED
		    units  CDATA #IMPLIED
		    target-height  CDATA #IMPLIED
		    target-width  CDATA #IMPLIED
                    src CDATA #IMPLIED>
	  <!ATTLIST Landmarks ulc-x  CDATA #IMPLIED
		    ulc-y  CDATA #IMPLIED
		    urc-x  CDATA #IMPLIED
		    urc-y  CDATA #IMPLIED
		    lrc-x  CDATA #IMPLIED
		    lrc-y  CDATA #IMPLIED
		    llc-x  CDATA #IMPLIED
		    llc-y  CDATA #IMPLIED>
	  <!ATTLIST Box x1 CDATA #REQUIRED 
		    y1 CDATA #REQUIRED 
		    x2 CDATA #IMPLIED 
		    y2 CDATA #IMPLIED
		    max-votes CDATA #IMPLIED
                    text-code CDATA #IMPLIED
		    text CDATA #REQUIRED>
	  <!ATTLIST Vote orient CDATA #REQUIRED
                    x1 CDATA #REQUIRED 
		    y1 CDATA #REQUIRED 
                    width CDATA #IMPLIED
                    height CDATA #IMPLIED 
                    text-code CDATA #IMPLIED
		    text CDATA #REQUIRED>
	  ]
>
"""
