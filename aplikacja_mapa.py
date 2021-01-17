#!/usr/bin/env python
# coding: utf-8

# In[1]:


import numpy as np
import pandas as pd 
import plotly.express as px
import json
import streamlit as st
import datetime
import re
import urllib.request
import sqlite3


# In[ ]:


# pre defined districts names for webscraping
dzielnice =  [  "mokotow","praga-poludnie","ursynow","wola","bielany","targowek","bemowo","srodmiescie","bialoleka","wawer",
                   "praga-polnoc","wlochy","wilanow","rembertow","wesola","ochota","ursus","zoliborz"]


# In[ ]:


# pre defined districts names for database/plots
dzielnice_polish =  [  "Mokotów", "Praga Południe","Ursynów","Wola","Bielany","Targówek","Bemowo","Śródmieście","Białołęka",
                         "Wawer","Praga Północ","Włochy","Wilanów","Rembertów","Wesoła","Ochota","Ursus","Żoliborz"]


# In[6]:


@st.cache
def load_data():
    #loading pre webscraped data
    return(pd.read_csv("WawPrices_long.csv"))


# In[ ]:


df_csv = load_data()


# In[ ]:


@st.cache
def webscrap_dzielnice():
    #webscraping function
    #checking if there are new observations, if not reading old data
    prices_dzielnice =[]
    for dzielnica in dzielnice:
        with urllib.request.urlopen("https://sonarhome.pl/ceny-mieszkan/warszawa/" + dzielnica) as response:
            html = response.readlines()
        list_raw = [str(x) for x in html]
        matching = [i for i, s in enumerate(list_raw) if "Prognozowana cena za" in s][0]
        html_rev = list_raw[0:matching]
        html_rev.reverse()
        first_number = [i for i, s in enumerate(html_rev) if "]," in s][0]
        last_number = [i for i, s in enumerate(html_rev) if "data" in s][0]
        prices_raw = html_rev[first_number+1:last_number]
        prices_raw.reverse()
        prices_clean = [re.sub(' ', '', str(x)) for x in prices_raw]
        last_numbers= [x.rfind(".") for x in prices_clean ]
        prices = [x[2:last_numbers[i]] for i, x in enumerate(prices_clean)]
        prices_dzielnice.append(prices)
        if len(prices)<=len(df_csv["Date"].unique()):
            return load_data()

    df_prices = pd.DataFrame(prices_dzielnice).transpose()
    df_prices.columns = dzielnice_polish
    times = pd.date_range('2018-01-01', periods=len(df_prices), freq='MS')
    df_prices = pd.concat([ pd.DataFrame({'Date':times}),df_prices],axis=1)
    df_prices_long = pd.melt(df_prices,id_vars="Date",var_name='District', value_name='Price')
    return(df_prices_long)


# In[ ]:


df = webscrap_dzielnice()


# In[ ]:


def create_db():
    #creating in memory database
    baza = sqlite3.connect(':memory:')
    df.to_sql('ap_db',baza,index=False)
    return baza


# In[ ]:


baz_1 = create_db()


# In[ ]:


def kwerenda(tekst = '''  SELECT * FROM ap_db  '''):
    #function to query data for plots
    c_1 = baz_1.cursor()
    c_1.execute(tekst)
    df_f2 = pd.DataFrame(c_1.fetchall())
    df_f2.columns = [description[0] for description in c_1.description]
    return(df_f2)


# In[7]:


@st.cache
def df_plot(x):
    return(df.query('Date=="'+x + '"'))


# In[8]:


@st.cache
def load_geojson():
    #reading geojson 
    with open('warszawa-dzielnice.geojson', encoding="utf-8") as response:
        counties = json.load(response)
    e= counties.copy()
    e['features'] = None
    e['features'] = counties['features'][1:19]
    return(e)


# In[65]:


st.title("Apartments prices in Warsaw districts in pln per square meter")


# In[10]:


#values to supply slider
foo = [round(2018 + x/12 + 1/12,2) for x in range(0,len(df['Date'].unique()),1)]


# In[2]:


st.sidebar.title("Choose type of the plot.")


# In[ ]:


def plot_map():
    #function to create map plot in plotly
    #reading geojson -> querying data -> plotting
    e = load_geojson()
    a =  st.slider("Date",min_value=(2018 + 1/12),max_value=foo[-1],step=1/12,key="a")
    foo_arg = foo.index(round(a,2))
    date_val = kwerenda(''' SELECT DISTINCT(Date) FROM ap_db ''')['Date'][foo_arg]
    df_to_plot = kwerenda(''' SELECT * FROM ap_db where Date == ''' + "'" + date_val + "'")
    min_1= kwerenda(''' SELECT MIN(Price) AS min FROM ap_db ''')['min'][0]
    max_1= kwerenda(''' SELECT MAX(Price) AS max FROM ap_db ''')['max'][0]
    st.write(date_val)
    fig = px.choropleth_mapbox(df_to_plot, geojson=e, color="Price",
                           locations="District", featureidkey="properties.name",
                           color_continuous_scale = px.colors.sequential.PuBu,
                           center={"lat": 52.229676, "lon": 21.012229},
                           mapbox_style="open-street-map", zoom=9,opacity=0.85,
                           range_color=[min_1,max_1])
    fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
    st.plotly_chart(fig)


# In[ ]:


def plot_hist():
    #function to plot histogram
    b =  st.slider("Date",min_value=(2018 + 1/12),max_value=foo[-1],step=1/12,key="b")
    foo_arg_2 = foo.index(round(b,2))
    date_val = kwerenda(''' SELECT DISTINCT(Date) FROM ap_db ''')['Date'][foo_arg_2]
    df_to_plot = kwerenda(''' SELECT * FROM ap_db where Date == ''' + "'" + date_val + "'")
    max_1= kwerenda(''' SELECT MAX(Price) AS max FROM ap_db ''')['max'][0]
    st.write(date_val)
    fig_2 = px.bar(df_to_plot, x='District', y='Price',range_y=[0,max_1])
    fig_2.update_traces(marker_color='indianred')
    fig_2.update_layout(barmode='stack', xaxis={'categoryorder':'total descending'},margin={"r":0,"t":0,"l":0,"b":0})
    st.plotly_chart(fig_2)


# In[ ]:


def plot_line():
    #function to plot line chart
    uni = df['District'].unique()
    district_selected = st.multiselect('Select districts', options = list(uni),default=uni)
    #mask_districts = df['District'].isin(district_selected)
    if len(district_selected)>0:
        district_selected.append('')
        kwerenda_text = ''' SELECT * FROM ap_db where District IN '''  + str(tuple(district_selected))
        df_to_plot = kwerenda(kwerenda_text)
        fig_3 = px.line(df_to_plot, x='Date', y='Price',color = "District")
        fig_3.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
        st.plotly_chart(fig_3)
    else:
        st.write("Please choose some districts :)")


# In[ ]:


#sidebar checkboxes
plot_type = st.sidebar.radio(
    "",
   ('Map', 'Histogram', 'Line'))

if plot_type == 'Map':
    plot_map()
elif plot_type == 'Histogram':
    plot_hist()
else:
    plot_line()

