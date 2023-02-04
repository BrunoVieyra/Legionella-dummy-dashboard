#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jan  3 13:36:01 2023

@author: brunovieyra
"""

import streamlit as st
import streamlit.components.v1 as components
from streamlit_agraph import agraph, Node, Edge, Config
import pandas as pd
import numpy as np
from neo4j import GraphDatabase
import json
import folium
from streamlit_folium import st_folium
from datetime import date
import os




# STREAMLIT LAYOUT
st.set_page_config(layout="wide")



# STREAMLIT HEADER MET DATUM SELECT:
st.title('IZB cluster analyse tool')
st.sidebar.title('Cluster visualisatie')

#slider maken voor selecteren van een datum
st.subheader('Selecteer een datum om de fiellabevents en context bezoeken op die dag te zien:')
dateSlider = st.slider("Selecteer datum voor weergave van Fieldlab events op die dag en contexten.",
    date(2021,1,1), date(2021,12,31), date(2021,7,1),
                       format ="YYYY/MMM/DD", 
                       label_visibility = "collapsed",
                       )

#Aangeven of evenementen door mochten gaan:
#CSV DATA inladen van OUR WORLD IN DATA
pubEvents = pd.read_csv('/Users/brunovieyra/OneDrive/Python/Streamlit/data_input_voor_COVID_Dashboard/public-events-covid.csv')
dfpubEvents = pd.DataFrame(pubEvents)    
closure_code= dfpubEvents.loc[(dfpubEvents['Day'] == dateSlider.isoformat()) | (dfpubEvents['Code'] == 'NLD'), 'cancel_public_events'].iloc[0]

if closure_code == 0:
    maatregel = "Op deze datum zijn er geen maatregelen voor het aflasten van 'public events'. Alles is open."
elif closure_code == 1:
    maatregel = "Op deze datum zijn werd het aflasten van 'public events' aanbevolen."
elif closure_code == 2:
    maatregel = "Op deze datum zijn alle 'public events' verplicht afgelast. Er zijn geen public events."    

st.write("### Sluitingsmaatregelen:", maatregel)
'bron: https://ourworldindata.org/covid-cancel-public-events'
          




# 2. FIELDLAB TABEL:
    
uri = "neo4j://localhost:7687"
driver = GraphDatabase.driver(uri, auth=("neo4j", "Bruno19-86"))

get_instances1 = """
match (f:FieldLabEvent)
Where f.Evenement is not null 
AND f.latitude is not null 
AND f.longitude is not null 
AND f.EndDate >= date('""" + dateSlider.isoformat() + """') >= f.StartDate
RETURN 
date(f.StartDate) as StartDate,  
date(f.EndDate) as EndDate,
f.Evenement as FieldlabEvenement,
f.EventID as EventID,
f.Municipality as Gemeente,
f.latitude as Latitude,
f.longitude as Longitude
Order by StartDate
                """

with driver.session() as graphDB_Session:
    resultF = graphDB_Session.run(get_instances1)
  
  

    dfFieldlab = pd.DataFrame([dict(record) for record in resultF])
    dfFieldlab = dfFieldlab.rename({'EventID':'id'}, axis =1)
    m = folium.Map(location=[51.95,4.4],width="%100",height="%100")
    folium.TileLayer('cartodbpositron').add_to(m)
    for index, row in dfFieldlab.iterrows():
        folium.CircleMarker(location=[row['Latitude'], row['Longitude']], radius=3, popup = row['FieldlabEvenement'], color = 'green').add_to(m)
      
driver.close()    
         

#kolommen maken voor de tabellen
colA, colB = st.columns(2)


with colA:
    st.write('### 1. FieldlabEvents - Zuid-Holland, jaar 2021')
    #rijnummer input selectbox
    selected_indices = st.number_input('Voer het rijnummer van het Fieldlab event uit de tabel hierboven in om matchende contexten te zoeken:', value = 1, step= 1)
    #dictionary van de geslecteerde fieldlabevent data:
    selected_rows = dfFieldlab.loc[selected_indices]
    #fieldlabtabel
    st.write(dfFieldlab)
    

    
# 3. STREAMLIT FIELDLAB TABEL

# dataframe maken voor de selectbox voor het filteren op context type:   
csv_cTypes = pd.read_csv('/Users/brunovieyra/OneDrive/Python/Streamlit/data_input_voor_COVID_Dashboard/ContextTypes.csv')
df_cTypes = pd.DataFrame(csv_cTypes) 

cTypes = [df_cTypes.loc[(df_cTypes['c.Type'] ==  "Bezoekersattracties"), 'c.Type'].iloc[0],
         df_cTypes.loc[(df_cTypes['c.Type'] ==  "Evenementen (congres, festival, etc)"), 'c.Type'].iloc[0],
         df_cTypes.loc[(df_cTypes['c.Type'] ==  "Overige geregistreerde contexts"), 'c.Type'].iloc[0] 
         ]

   
#De NEO query naar dataframe:

uri = "neo4j://localhost:7687"
driver = GraphDatabase.driver(uri, auth=("neo4j", "Bruno19-86"))

get_instances2 = """
Match (f:FieldLabEvent)
Where f.EventID = '""" + selected_rows[['id']][0] + """'
With f, point({latitude: toFloat(f.latitude), longitude: toFloat(f.longitude)}) as Locatiepunt1
MATCH path = (c:Context)<-[rel]-(i:Index)
WHERE (date('""" + dateSlider.isoformat() + """') + duration({days: 14})) >= date(i.EZD) >= (date('""" + dateSlider.isoformat() + """')+ duration({days: 2})) 
AND date('""" + dateSlider.isoformat() + """') >= date(rel.StartDate) >= date('""" + dateSlider.isoformat() + """')
AND c.latitude is not null
AND c.longitude is not null
With f,c,i,rel, Distance(point({latitude: c.latitude, longitude: c.longitude}), Locatiepunt1) as Afstand
RETURN c.Context as ContextName,
Afstand as AfstandTotFieldlab,
date(rel.StartDate) as StartDate, 
date(rel.EndDate) as EndDate,
count(i.EZD) as AantalIndexenMetPassendeIncubatietijd,
c.Type as ContextType,
c.latitude as Lat,
c.longitude as Lon,
c.ContextID as ContextID

Order by AfstandTotFieldlab asc
                """



with driver.session() as graphDB_Session:
    result = graphDB_Session.run(get_instances2)
#dataframes maken van de NEO export:
    dfcTemp = pd.DataFrame([dict(record) for record in result])
#row_id aanmaken voor 'active cell' callback  
    dfcTemp = dfcTemp.rename({'ContextID':'id'}, axis =1)
    
#STREAMLIT CONTEXTTABEL EN CONTEXT TyPE SELECTIE  
with colB:    
    cTypeSelect = st.multiselect(
                            'Selecteer context types:',
                                df_cTypes['c.Type'], cTypes
                                )

    dfContext = dfcTemp[dfcTemp['ContextType'].isin(cTypeSelect)]
    st.write('### 2. Contexten - gekoppelde cases met datum Fieldlab event in incubatietijd.')
    
    
    st.write(dfContext)
    for index, row in dfContext.iterrows():
        folium.CircleMarker(location=[row['Lat'], row['Lon']], radius=3, popup = row['ContextName'], color = '#f5cd1d').add_to(m)
    

driver.close()


    
    
#STREAMLIT SIDEBAR: info geselcteerde contxt
st.sidebar.write('### Geselecteerde Fieldlab event: ' + selected_rows[['id']][0], selected_rows)



# STREAMLIT FOLIUM MAP
#Geslecteerd Fieldlab event rood laten kleuren, en grotere radius geven:
folium.CircleMarker(location=[selected_rows[['Latitude']][0], selected_rows[['Longitude']][0]], 
                    radius=5, 
                    popup = selected_rows[['FieldlabEvenement']][0], 
                    color = 'red'
                    ).add_to(m)

st_folium(m, width= 1200, height= 800) 







