import json
import copy

import numpy as np
import pandas as pd

import plotly
import plotly.offline as py
import plotly.graph_objs as go
import plotly.figure_factory as ff

from fuzzywuzzy import fuzz, process

from matplotlib.colors import Normalize
from matplotlib import cm

from itertools import product
from collections import Counter

from config import *
# print("everything already installed")


def get_centers():
    lon, lat = [], []

    for k in range(n_provinces):
        geometry = geojson['features'][k]['geometry']

        if geometry['type'] == 'Polygon':
            coords = np.array(geometry['coordinates'][0])
        elif geometry['type'] == 'MultiPolygon':
            coords = np.array(geometry['coordinates'][0][0])

        lon.append(sum(coords[:,0]) / len(coords[:,0]))
        lat.append(sum(coords[:,1]) / len(coords[:,1]))

    return lon, lat

def match_regions(list1, list2):
    matched = [
        process.extract(list1[i], list2, limit=1, scorer=fuzz.partial_ratio)[
            0
        ][0]
        for i in range(len(list1))
    ]

    return {key: value for (key, value) in zip(list1, matched)}


def make_sources():
    geojson_copy = copy.deepcopy(geojson['features'])

    return [
        dict(type='FeatureCollection', features=[feature])
        for feature in geojson_copy
    ]

def scalarmappable(cmap, cmin, cmax):
    colormap = cm.get_cmap(cmap)
    norm = Normalize(vmin=cmin, vmax=cmax)
    return cm.ScalarMappable(norm=norm, cmap=colormap)

def get_scatter_colors(sm, df):
    grey = 'rgba(128,128,128,1)'
    return ['rgba' + str(sm.to_rgba(m, bytes = True, alpha = 1)) if not np.isnan(m) else grey for m in df]

def get_colorscale(sm, df, cmin, cmax):
    xrange = np.linspace(0, 1, len(df))
    values = np.linspace(cmin, cmax, len(df))
    return [[i, 'rgba' + str(sm.to_rgba(v, bytes = True))] for i,v in zip(xrange, values) ]

def get_hover_text(df) :
    text_value = (df).astype(str) + ""
    with_data = '<b>{}</b> <br> {}'
    no_data = '<b>{}</b> <br> no data'

    return [with_data.format(p,v) if v != 'nan%' else no_data.format(p) for p,v in zip(df.index, text_value)]

def get_data_layout(df):

    layers = []
    for i in range(len(data_slider)):

        scatter_colors = df[i]['marker']['color']

        layer=([dict(sourcetype = 'geojson',
                      source =sources[k],
                      below="",
                      type = 'line',
                      line = dict(width = 1),
                      color = 'black',
                      ) for k in range(n_provinces)
                  ] +

                [dict(sourcetype = 'geojson',
                      source =sources[k],
                      below="water",
                      type = 'fill',
                      color = scatter_colors[k],
                      opacity=0.8,
                     ) for k in range(n_provinces)]
                 )

        layers.append(layer)

    return layers

if __name__ == "__main__":

    df = pd.read_csv("/home/muhammad/Envs/map_proj/code/Map_Visualization_with_Plotly/Interactive_Visualization/Census_2016_Population_by_age_groups_and_sex (Edited).csv", index_col=0)
    columns = df.columns.tolist()
    # print(columns[:3])

    with open('/home/muhammad/Envs/map_proj/code/Map_Visualization_with_Plotly/Interactive_Visualization/iran_geo.json') as f:
        geojson = json.load(f)

    n_provinces = len(geojson['features'])
    provinces_names = [geojson['features'][k]['properties']['NAME_1'] for k in range(n_provinces)]
    # print("there are {} provinces ".format(n_provinces))
    # print(provinces_names)

    match_dict = match_regions(df.index, provinces_names)
    # print(match_dict)

    sources = make_sources()
    lons, lats = get_centers()

    data_slider = []
    for age in columns[:3]:
        age_data = df[age]
        age_data.name = 'province'
        # print(age_data.head())

        df_tmp = age_data.copy()
        df_tmp.index = df_tmp.index.map(match_dict)
        df_tmp = df_tmp[~df_tmp.index.duplicated(keep=False)]

        df_reindexed = df_tmp.reindex(index = provinces_names)

        colormap = 'Blues'
        cmin = df_reindexed.min()
        cmax = df_reindexed.max()

        sm = scalarmappable(colormap, cmin, cmax)
        scatter_colors = get_scatter_colors(sm, df_reindexed)
        colorscale = get_colorscale(sm, df_reindexed, cmin, cmax)
        hover_text = get_hover_text(df_reindexed)

        tickformat = ""

        data = dict(type='scattermapbox',
                    lat=lats,
                    lon=lons,
                    mode='markers',
                    text=hover_text,
                    marker=dict(size=1,
                                color=scatter_colors,
                                showscale = True,
                                cmin = df_reindexed.min(),
                                cmax = df_reindexed.max(),
                                colorscale = colorscale,
                                colorbar = dict(tickformat = tickformat)
                               ),
                    showlegend=False,
                    hoverinfo='text'
                    )


        data_slider.append(data)

    layers = get_data_layout(data_slider)

    visibility = []
    for i in range(len(data_slider)):
        list = [False] * len(data_slider)
        list[i] = True
        visibility.append(list)

    steps = []
    for i in range(len(data_slider)):
        step = dict(method='update',
                    args=[{'visible': visibility[i]},
                          {'mapbox.layers': layers[i]}],
                    label='Age {}' .format(i),)
        steps.append(step)

    sliders = [dict(steps=steps)]

    layout = dict(title="IRAN 2016 POPULATION",
                  autosize=False,
                  width=700,
                  height=800,
                  hovermode='closest',

                  mapbox=dict(accesstoken=MAPBOX_APIKEY,
                              bearing=0,
                              center=dict(
                                        lat=35.715298,
                                        lon=51.404343),
                              pitch=0,
                              zoom=4.9,
                              style = 'dark'),
                  sliders=sliders,
                  )

    fig = dict(data=data_slider, layout=layout)
    py.plot(fig)
