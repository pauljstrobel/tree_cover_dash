import dash
from dash import dcc, html, Input, Output
import plotly.graph_objects as go
import pandas as pd
import geopandas as gpd
import numpy as np
import os

# Initialize Dash app only once
app = dash.Dash(__name__, 
                meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}],
                external_stylesheets=['https://fonts.googleapis.com/css2?family=Open+Sans:wght@300;400;600&display=swap'])

# Define server variable - this is what Render will use
server = app.server

# Make sure the data path is correctly handled
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
data_path = os.path.join(BASE_DIR, "data", "results_gdf.pkl")

# Use a try-except block to help debug data loading issues
try:
    results_gdf = pd.read_pickle(data_path)
    # Get list of available cities
    cities = sorted(results_gdf["location"].unique())
except Exception as e:
    print(f"Error loading data: {e}")
    # Provide a fallback to prevent app from crashing if data isn't found
    results_gdf = pd.DataFrame()
    cities = ["No data available"]
    
# Custom CSS
app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <style>
            body {
                font-family: 'Open Sans', sans-serif;
                margin: 0;
                background-color: #fafafa;
                color: #333;
            }
            .container {
                max-width: 1200px;
                margin: 0 auto;
                padding: 2rem;
            }
            .header {
                text-align: center;
                margin-bottom: 2rem;
                padding-bottom: 1rem;
                border-bottom: 1px solid #eee;
            }
            .intro-text {
                margin: 0 auto 2rem;
                color: #666;
                line-height: 1.6;
                max-width: 800px;
                font-weight: 300;
            }
            .control-panel {
                background-color: white;
                border-radius: 8px;
                padding: 1.5rem;
                box-shadow: 0 1px 3px rgba(0,0,0,0.08);
                margin-bottom: 2rem;
            }
            .graph-container {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 2rem;
            }
            .graph-card {
                background-color: white;
                border-radius: 8px;
                overflow: hidden;
                box-shadow: 0 1px 3px rgba(0,0,0,0.08);
            }
            h2 {
                font-weight: 600;
                color: #333;
                margin-top: 0.5rem;
            }
            .dropdown-label {
                font-weight: 600;
                margin-bottom: 0.5rem;
                display: block;
                color: #555;
                font-size: 0.9rem;
            }
            @media (max-width: 768px) {
                .graph-container {
                    grid-template-columns: 1fr;
                }
            }
        </style>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
'''

app.layout = html.Div(className="container", children=[
    html.Div(className="header", children=[
        html.H2("Tree Cover Change Dashboard"),
        html.Div(className="intro-text", children=[
            html.P("Explore 20 years of metropolitan tree cover evolution across global metropolitan regions with this interactive dashboard. Compare canopy changes from 2002-2022 along a 500 meter grid based on approximate data from the MODIS Vegetation Continuous Fields product.")
        ]),
    ]),
    
    html.Div(className="control-panel", children=[
        html.Div(style={'display': 'flex', 'gap': '2rem', 'flex-wrap': 'wrap', 'margin-bottom': '1.5rem'}, children=[
            html.Div(style={'flex': '1', 'min-width': '250px'}, children=[
                html.Label("Select City 1:", className="dropdown-label"),
                dcc.Dropdown(
                    id='city1', 
                    options=[{'label': c, 'value': c} for c in cities], 
                    value=cities[0],
                    style={'width': '100%'}
                )
            ]),
            html.Div(style={'flex': '1', 'min-width': '250px'}, children=[
                html.Label("Select City 2:", className="dropdown-label"),
                dcc.Dropdown(
                    id='city2', 
                    options=[{'label': c, 'value': c} for c in cities], 
                    value=cities[1],
                    style={'width': '100%'}
                )
            ]),
        ]),
        
        html.Div(style={'margin-top': '0.5rem'}, children=[
            html.Label("View Mode:", className="dropdown-label"),
            dcc.RadioItems(
                id='view-mode',
                options=[
                    {'label': 'Map', 'value': 'map'},
                    {'label': 'Grid', 'value': 'grid'}
                ],
                value='map',
                labelStyle={'display': 'inline-block', 'margin-right': '20px', 'cursor': 'pointer', 'font-weight': '300'}
            )
        ]),
    ]),
    
    html.Div(className="graph-container", children=[
        html.Div(className="graph-card", children=[
            dcc.Graph(id='graph1')
        ]),
        html.Div(className="graph-card", children=[
            dcc.Graph(id='graph2')
        ]),
    ])
])

@app.callback(
    Output('graph1', 'figure'),
    Output('graph2', 'figure'),
    Input('city1', 'value'),
    Input('city2', 'value'),
    Input('view-mode', 'value')
)
def update_graphs(city1, city2, mode):
    fig1 = make_plot(results_gdf, city1, mode)
    fig2 = make_plot(results_gdf, city2, mode)
    return fig1, fig2

def make_plot(df, city, mode):
    data = df[df["location"] == city].copy()

    temp = data.set_geometry('point_geom').to_crs("EPSG:4326")
    data['lat'] = temp.geometry.y
    data['lon'] = temp.geometry.x

    if mode == 'map':
        # Determine hover text color based on background color
        hover_text_colors = []
        for color in data['color']:
            # We'll use white text for all markers for better consistency
            hover_text_colors.append('white')
        
        data['hover_text_color'] = hover_text_colors

        fig = go.Figure()
        fig.add_trace(go.Scattermapbox(
            lat=data['lat'],
            lon=data['lon'],
            mode='markers',
            marker=dict(size=data['markersize'], color=data['color']),
            name='Points',
            customdata=data[['tree_cover_change', 'tree_cover_2002', 'tree_cover_2022', 'hover_text_color']].values,
            hovertemplate=(
                "<span style='color:%{customdata[3]}'>Type: " + 
                ("Decrease" if "%{customdata[0]}" < "0" else "Increase" if "%{customdata[0]}" > "0" else "No Change") + 
                "<br>Change: %{customdata[0]:.2f} %<br>" +
                "2002: %{customdata[1]:.2f} %<br>" +
                "2022: %{customdata[2]:.2f} %</span><extra></extra>"
            ),
            hoverlabel=dict(
                bgcolor=data['color'],
                bordercolor='rgba(255,255,255,1.0)',
            )
        ))
        fig.update_layout(
            mapbox=dict(
                style="carto-positron",
                center=dict(lat=data['lat'].mean(), lon=data['lon'].mean()),
                zoom=10
            ),
            margin=dict(l=5, r=5, t=30, b=5),
            height=600,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            title=dict(
                text=city,
                font=dict(family="Open Sans, sans-serif bold", size=12, color='black'),
                x=0.5,  # Center the title
                y=0.98
            )
        )
        return fig

    else:  # grid view
        data = data.sort_values(by="tree_cover_change")
        n_cols = 80
        data['x_coord'] = [i % n_cols for i in range(len(data))]
        data['y_coord'] = [-(i // n_cols) for i in range(len(data))]
        data['marker_size'] = data['tree_cover_change'].abs() / 2
        data.loc[data['tree_cover_change'] == 0, 'marker_size'] = 0.1

        fig = go.Figure()

        for filt, label, hover_color in [
            (data['tree_cover_change'] < 0, 'Decrease', 'Decrease'),
            (data['tree_cover_change'] > 0, 'Increase', 'Increase'),
            (data['tree_cover_change'] == 0, 'No Change', 'No Change')
        ]:
            sub = data[filt]
            if sub.empty: continue
            color = sub['color'] if label != 'No Change' else '#E6E6E6'
            
            # Add white text color for hover info
            sub['hover_text_color'] = 'white'

            fig.add_trace(go.Scatter(
                x=sub['x_coord'],
                y=sub['y_coord'],
                mode='markers',
                marker=dict(color=color, size=sub['marker_size'], opacity=0.9),
                name=label,
                customdata=sub[['tree_cover_change', 'tree_cover_2002', 'tree_cover_2022', 'hover_text_color']].values,
                hovertemplate=(
                    "<span style='color:%{customdata[3]}'>Type: " + label + "<br>" +
                    "Change: %{customdata[0]:.2f} %<br>" +
                    "2002: %{customdata[1]:.2f} %<br>" +
                    "2022: %{customdata[2]:.2f} %</span><extra></extra>"
                ),
                hoverlabel=dict(
                    bgcolor=color,
                    bordercolor='rgba(255,255,255,1.0)',
                )
            ))

        fig.update_layout(
            xaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
            yaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
            height=600,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            showlegend=False,
            margin=dict(l=5, r=5, t=30, b=5),
            title=dict(
                text=city,
                font=dict(family="Open Sans, sans-serif", size=12, color='black'),
                x=0.5,  # Center the title
                y=0.98
            )
        )
        return fig

if __name__ == "__main__":
    app.run(debug=True)
server = app.server