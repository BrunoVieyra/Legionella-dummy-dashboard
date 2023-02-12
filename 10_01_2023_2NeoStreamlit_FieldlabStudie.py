#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Feb  4 16:51:16 2023

_I5F80Ga6FcrJsX8D-xNMCn6cLbIeYdoOSNARmUeFYo

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
from folium.plugins import MeasureControl
from PIL import Image

# STREAMLIT LAYOUT
st.set_page_config(layout="wide")

#bron dataframe:
dfRaw = pd.read_csv('dfRaw_shifted.csv')

# STREAMLIT TITEL en context selectie (nog niet werkend):
st.header('Legionella clusterdetectie tool DEMO - :red[data is fictief! Geen echte casuïstiek]')

st.sidebar.subheader('Legenda:')
st.sidebar.image(Image.open('legenda folium map.png'),use_column_width = 'always')




#___________________________________________________________________________________________
#DATAFRAMES AANMAKEN
#Folium dataframe maken voor a_indexen
dfA_index= dfRaw[['a_label', 'a_id', 'a_prop_HPZone status', 'a_prop_EZD', 'a_prop_Kweek', 'a_prop_LegionellaType', 
                   'a_prop_BEL1', 'a_prop_BEL2', 'a_prop_BEL4',
                   'a_prop_latitude', 'a_prop_longitude']].copy()

dfA_index.rename(columns = {'a_label':'label', 'a_id':'case id', 'a_prop_HPZone status': 'HPZone status', 'a_prop_EZD': 'EZD', 
                            'a_prop_Kweek': 'sputumkweek ingezet', 'a_prop_LegionellaType': 'typering', 
                            'a_prop_latitude' : 'lat', 'a_prop_longitude' : 'lon',
                            'a_prop_BEL1': 'BEL1', 'a_prop_BEL2':'BEL2', 'a_prop_BEL3': 'BEL3', 'a_prop_BEL4': 'BEL4',
                            }, inplace = True)
dfA_index = dfA_index.astype({'case id': 'int'})

# Folium dataframe maken voor b_indexen
dfB_index = dfRaw[['b_label', 'b_id', 'b_prop_HPZone status', 'b_prop_EZD','b_prop_BronType', 'b_prop_LegionellaType', 
                   'b_prop_BEL1', 'b_prop_BEL2', 'b_prop_BEL4',
                   'b_prop_latitude', 'b_prop_longitude',]].copy()

dfB_index.rename(columns = {'b_label':'label', 'b_id':'case id', 'b_prop_HPZone status': 'HPZone status', 'b_prop_EZD': 'EZD', 
                            'b_prop_BronType': 'Bron Type', 'b_prop_Kweek': 'sputumkweek ingezet', 'b_prop_LegionellaType': 'typering', 
                            'b_prop_latitude' : 'lat', 'b_prop_longitude' : 'lon',
                            'b_prop_BEL1': 'BEL1', 'b_prop_BEL2':'BEL2', 'b_prop_BEL3': 'BEL3', 'b_prop_BEL4': 'BEL4'
                            }, inplace = True)

# Folium dataframe maken voor b_contexten
dfB_context = dfRaw[['rel_label', 'rel_prop_BEL1', 'rel_prop_BEL2', 'rel_prop_BEL4',
                     'b_prop_latitude', 'b_prop_longitude', 'a_prop_latitude', 'a_prop_longitude', 'a_id', 'b_id', 'rel_id']].copy()

dfB_context.rename(columns = {'rel_label':'label', 'rel_prop_BEL1': 'BEL1', 'rel_prop_BEL2':'BEL2', 'rel_prop_BEL3': 'BEL3', 'rel_prop_BEL4': 'BEL4',
                              'b_prop_latitude': 'blat', 'b_prop_longitude' : 'blon', 'a_prop_latitude' : 'alat', 'a_prop_longitude' : 'alon'
                            }, inplace = True)


#STREAMLIT case en relatie TABEL

dfTabelB = dfB_index[dfB_index["label"] == 'Index'].dropna(subset=["lat"])
dfTabelB = dfTabelB.drop_duplicates(subset=["case id"], keep='first')

dfTabelA = dfA_index.dropna(subset=["lat"])
dfTabelA = dfTabelA.drop_duplicates(subset=["case id"], keep='first')

dfTabel = pd.concat([dfTabelA, dfTabelB], ignore_index=True, sort=False)
dfTabel = dfTabel.drop_duplicates(subset=["case id"], keep='first')

dfTabel = dfTabel.astype({'case id': 'int'})

#___________________________________________________________________________
#Sidebar BEL criteria selecteren
st.sidebar.subheader('Selecteer BEL criteria:')


# functie  if statements nog verbeteren geeft nu een error als er geen BEL case is (huiigde set is er geen BEL3 case)
def filter_data(dfTabel, selected_columns):
    if not selected_columns:
        return dfTabel
    mask = dfTabel[selected_columns].notnull().any(axis=1)
    dfTabel = dfTabel[mask]
    dfTabel = dfTabel.reset_index(drop=True)
    return dfTabel


selected_BEL_columns = []
if st.sidebar.checkbox("BEL1 - locatiecluster", help= 'Er is sprake van een locatiecluster van 2 of meer patiënten binnen 2 jaar gerelateerd aan dezelfde potentiële bron.'):
    selected_BEL_columns.append('BEL1')
    
if st.sidebar.checkbox("BEL2 - geografisch case cluster", help= 'Er is sprake van een geografisch cluster van 3 of meer patiënten binnen een half jaar, woonachtig binnen een straal van 1 km van elkaar.'):
    selected_BEL_columns.append('BEL2')
    

if st.sidebar.checkbox("BEL3 - solitaire patiënt zorginstelling", help= 'Er is een solitaire patiënt in een zorginstelling.'):
    st.sidebar.write(':red[Er zijn geen BEL3 cases in deze database.]')
            
if st.sidebar.checkbox("BEL4 - positieve sputumkweek", help= 'Er is een solitaire patiënt met een positieve sputumkweek, waarbij het woonhuis niet de enige potentiële besmettingsbron is.'):
    selected_BEL_columns.append('BEL4')

dfTabel = filter_data(dfTabel, selected_BEL_columns)




# A indexen filteren voor folium:
PredfA_index_filtered = dfRaw[dfRaw['a_id'].isin(dfTabel['case id'])]
dfA_index_filtered= PredfA_index_filtered[['a_label', 'a_id', 'a_prop_HPZone status', 'a_prop_EZD', 'a_prop_Kweek', 'a_prop_LegionellaType', 
                   'a_prop_BEL1', 'a_prop_BEL2', 'a_prop_BEL4',
                   'a_prop_latitude', 'a_prop_longitude',]].copy()

dfA_index_filtered.rename(columns = {'a_label':'label', 'a_id':'case id', 'a_prop_HPZone status':'HPZone status', 'a_prop_EZD': 'EZD', 
                            'a_prop_Kweek': 'sputumkweek ingezet', 'a_prop_LegionellaType': 'typering', 
                            'a_prop_latitude' : 'lat', 'a_prop_longitude' : 'lon',
                            'a_prop_BEL1': 'BEL1', 'a_prop_BEL2':'BEL2', 'a_prop_BEL3': 'BEL3', 'a_prop_BEL4': 'BEL4'
                            }, inplace = True)
dfA_index_filtered = dfA_index_filtered.astype({'case id': 'int'})


# B indexen filteren voor folium:
PredfB_index_filtered = dfRaw[dfRaw['a_id'].isin(dfTabel['case id'])]
dfB_index_filtered = PredfB_index_filtered[['b_label', 'b_id', 'b_prop_HPZone status', 'b_prop_EZD', 'b_prop_BronType','b_prop_LegionellaType', 
                   'b_prop_BEL1', 'b_prop_BEL2', 'b_prop_BEL4',
                   'b_prop_latitude', 'b_prop_longitude',]].copy()

dfB_index_filtered.rename(columns = {'b_label':'label', 'b_id':'case id','b_prop_HPZone status': 'HPZone status', 'b_prop_EZD': 'EZD', 
                            'b_prop_BronType':'Bron Type', 'b_prop_Kweek': 'sputumkweek ingezet', 'b_prop_LegionellaType': 'typering', 
                            'b_prop_latitude' : 'lat', 'b_prop_longitude' : 'lon',
                            'b_prop_BEL1': 'BEL1', 'b_prop_BEL2':'BEL2', 'b_prop_BEL3': 'BEL3', 'b_prop_BEL4': 'BEL4'
                            }, inplace = True)

#contexten filteren voor folium
Pre_dfB_context_filtered = dfRaw[dfRaw['a_id'].isin(dfTabel['case id'])]
dfB_context_filtered = Pre_dfB_context_filtered[['rel_label', 'rel_prop_BEL1', 'rel_prop_BEL2', 'rel_prop_BEL4',
                     'b_prop_latitude', 'b_prop_longitude', 'a_prop_latitude', 'a_prop_longitude','a_id', 'b_id', 'rel_id']].copy()

dfB_context_filtered.rename(columns = {'rel_label':'label', 'rel_prop_BEL1': 'BEL1', 'rel_prop_BEL2':'BEL2', 'rel_prop_BEL3': 'BEL3', 'rel_prop_BEL4': 'BEL4',
                              'b_prop_latitude': 'blat', 'b_prop_longitude' : 'blon', 'a_prop_latitude' : 'alat', 'a_prop_longitude' : 'alon'
                            }, inplace = True)


#______________________________________________________________________________
# FOLIUM map opbouwen


m = folium.Map(location=[51.75, 4.85],width= '%100',height="%100", zoom_start=11)
m.add_child(MeasureControl())
folium.TileLayer('cartodbpositron').add_to(m)



# a_indexen plotten in folium:
for index, row in dfA_index_filtered.iterrows():
    html = "<table>"
    for col in dfA_index_filtered.columns:
        if pd.notnull(row[col] ):
            html += "<tr><td><b>" + col + ":&nbsp</b></td><td>" + str(row[col]) + "<br></td></tr>"
            html += "</table>"
    if pd.isna(row["lat"]) == True:
        pass
    elif row["HPZone status"] == 'open':
        popup_info = folium.Popup(html, max_width=500)
        hover_info = int(row['case id'])
        folium.CircleMarker(location=[row['lat'], row['lon']], radius=4, popup = popup_info, tooltip = 'case id: ' + str(hover_info), color = '#e01202', fill = True, fill_color = '#e01202').add_to(m)
    elif row["HPZone status"] == 'closed':
        popup_info = folium.Popup(html, max_width=500)
        hover_info = int(row['case id'])
        folium.CircleMarker(location=[row['lat'], row['lon']], radius=4, popup = popup_info, tooltip = 'case id: ' + str(hover_info), color = '#fa9d96', fill = True).add_to(m)    

# b_indexen en contexten plotten in folium:
for index, row in dfB_index_filtered.iterrows():
    html = "<table>"
    for col in dfB_index_filtered.columns:
        if pd.notnull(row[col] ):
            html += "<tr><td><b>" + col + ":&nbsp</b></td><td>" + str(row[col]) + "<br></td></tr>"
            html += "</table>"
    if pd.isna(row["lat"]) == True:
        pass
    else:
        popup_info = folium.Popup(html, max_width=500)
        hover_info = int(row['case id'])
        if row["HPZone status"] == 'open':
            folium.CircleMarker(location=[row['lat'], row['lon']], radius=4, color = '#e01202', fill = True, popup= popup_info, tooltip = 'case id: ' + str(hover_info)).add_to(m)
        elif row["HPZone status"] == 'closed':
            folium.CircleMarker(location=[row['lat'], row['lon']], radius=4, color = '#fa9d96', fill = True, popup= popup_info, tooltip = 'case id: ' + str(hover_info)).add_to(m)
        else:
            folium.CircleMarker(location=[row['lat'], row['lon']], radius=4, color = '#ffcc26', fill = True, popup= popup_info, tooltip = 'case id: ' + str(hover_info)).add_to(m)

# Link case markers to their corresponding source locations
for i, row in dfB_context_filtered.iterrows():
    html = "<table>"
    for col in dfB_context_filtered.columns:
        if pd.notnull(row[col] ):
            html += "<tr><td><b>" + col + ":&nbsp</b></td><td>" + str(row[col]) + "<br></td></tr>"
            html += "</table>"
    if not (pd.isna(row["blat"]) == True) and not (pd.isna(row["alat"]) == True):
        popup_info = folium.Popup(html, max_width=500)
        index_loc = [row['alat'], row['alon']]
        bron_loc = [row['blat'], row['blon']]
        folium.PolyLine(locations=[index_loc, bron_loc], color="#46484a", popup= popup_info, weight=1, opacity=0.4).add_to(m)
    else:
        pass



#____________________________________________________
# Een case selecteren:

st.sidebar.subheader('Voer het index **case id** nummer in om te selecteren:')
selected_indices = st.sidebar.number_input('voer case id in:',label_visibility= 'collapsed', value = dfTabel['case id'][0], step= 1)
dfselected_rows = dfTabel[dfTabel['case id'] == selected_indices]
   

selected_rows = dfselected_rows.transpose()

# Geselecteerde case plotten in folium:
for index, row in dfselected_rows.iterrows():
    html = "<table>"
    for col in dfselected_rows.columns:
        html += "<tr><td><b>" + col + ":&nbsp</b></td><td>" + str(row[col]) + "<br></td></tr>"
        html += "</table>"      
    popup_info = folium.Popup(html, max_width=500)
    hover_info = int(row['case id'])
    folium.CircleMarker(location=[row['lat'], row['lon']], radius=2, color = 'blue').add_to(m)
    folium.CircleMarker(location=[row['lat'], row['lon']], radius=4, popup = popup_info, color = 'blue', fill = True, tooltip = hover_info).add_to(m)
    folium.Circle(location=[row['lat'], row['lon']], radius=1000, color = 'blue', fill=False, opacity=0.3).add_to(m)


#___________________________________________________________________________
# STREAMLIT DASHBOARD LAYOUT
col1, col2 = st.columns([6,4])
with col1:
    st.subheader('1. Case Tabel')
    st.caption('Indien **geen** BEL criterium aangevinkt in de linker balk worden alle cases van de afgelopen 2 jaar weergegeven.')
    
    # dfTabel opschonen:
    streamlit_dfTabel= dfTabel[['label', 'case id', 'HPZone status', 'EZD', 'sputumkweek ingezet', 'typering', 
                                'BEL1', 'BEL2', 'BEL4' 
                       ]].copy()
    streamlit_dfTabel= streamlit_dfTabel.astype({'case id': 'str'})    
        
    st.dataframe(streamlit_dfTabel, height= 300)
    


#_________________________________________________________________________
#Nodes dataframe vanuit relationships dataframe aanmaken
dfNodesStart= dfA_index_filtered[['case id','label', 'HPZone status']]
dfNodesStat=rt = dfNodesStart.dropna(subset=["case id"]) 
dfNodes= dfNodesStart.rename({'case id': 'ID', 'label': 'Label'}, axis= 1)
dfNodesEnd= dfB_index_filtered[['case id','label', 'HPZone status','Bron Type']]
dfNodesEnd= dfNodesEnd.rename({'case id': 'ID', 'label': 'Label'}, axis= 1)
dfNodesEnd = dfNodesEnd.dropna(subset=["ID"]) 
dfNodes= dfNodes.append(dfNodesEnd)
dfNodes= dfNodes.drop_duplicates(subset= ['ID'])     
#Edges dataframe aanmaken 
dfEdges= dfB_context_filtered[['rel_id', 'a_id', 'b_id', 'label']]
dfEdges = dfEdges.dropna(subset=["rel_id"]) 
dfEdges= dfEdges.drop_duplicates(subset= ['rel_id']) 
    

nodes = []
for row in dfNodes.to_dict(orient='records'):
    
    if row['Label'] == 'Index' and row['ID'] in dfselected_rows['case id'].values:
        kleur = '#268bff'
        lbl= row['Label']
    elif row['Label'] == 'Index' and row['HPZone status'] == 'open':
        kleur = '#e01202' 
        lbl= row['Label']
    elif row['Label'] == 'Index' and row['HPZone status'] == 'closed':
        kleur = '#fa9d96'    
        lbl= row['Label']
    elif row['Label'] == 'Context':
        kleur = '#ffcc26'
        if pd.notnull(row['Bron Type']):
            lbl = row['Bron Type']
        else:
            lbl= row['Label']
    ID = row['ID']
    nodes.append( Node(
        id = ID,
        size = 25,
        label = lbl,
        color = kleur,
        ))


      

edges = []
for row in dfEdges.to_dict(orient='records'):
    ID, src, trg, lbl = row['rel_id'], row['a_id'], row['b_id'], row['label']
    edges.append( Edge(
        id= ID,
        source = src,
        label = ' ',
        target= trg,
    )) 

# STREAMLIT GRAPH
config = Config(nodeHighlightBehavior=True,
                highlightColor="#F7A7A6",
                height=300, width= 700
                # **kwargs
                ) 

with col2:
    st.subheader('2. Schematische weergave')
    st.caption('Klik op een case om **case id** in beeld te krijgen')
    agraph(nodes=nodes,
           edges=edges,
           config=config)


    

#_________________________________________________________________________
#STREAMLIT SIDEBAR: info geselcteerde contxt
#st.sidebar.write('geselecteerde de :blue[blauwe] :large_blue_circle: op de kaart, met een :blue[blauw] gemarkeerde straal rondom van **1 km**.')
st.sidebar.subheader('Details geselecteerde case:')
st.sidebar.table(selected_rows)




# STREAMLIT FOLIUM MAP

st.subheader('3. Geografische weergave geselecteerde cases + potentiële bronnen')
st_folium(m, width = 1200, height= 450)



