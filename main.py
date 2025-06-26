import dash
from dash import dcc, html, Input, Output, State
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import simpy
import random
import numpy as np

def run_simulation(jumlah_loket, waktu_simulasi, rata_kedatangan, rata_layanan, random_seed):
    data_waktu_tunggu = []
    data_waktu_sistem = []
    histori_panjang_antrean = []
    histori_waktu = []
    histori_server_sibuk = []

    def sumber_pelanggan(env, loket):
        id_pelanggan = 0
        while True:
            yield env.timeout(random.expovariate(1.0 / rata_kedatangan))
            id_pelanggan += 1
            env.process(pelanggan(env, f'Pelanggan {id_pelanggan}', loket))

    def pelanggan(env, nama, loket):
        waktu_datang = env.now
        with loket.request() as request:
            yield request
            waktu_mulai_layanan = env.now
            waktu_tunggu = waktu_mulai_layanan - waktu_datang
            data_waktu_tunggu.append(waktu_tunggu)
            waktu_layanan_dihasilkan = random.expovariate(1.0 / rata_layanan)
            yield env.timeout(waktu_layanan_dihasilkan)
            waktu_selesai = env.now
            waktu_di_sistem = waktu_selesai - waktu_datang
            data_waktu_sistem.append(waktu_di_sistem)

    def monitor_antrean(env, loket):
        while True:
            histori_waktu.append(env.now)
            histori_panjang_antrean.append(len(loket.queue))
            histori_server_sibuk.append(loket.count)
            yield env.timeout(1.0)

    random.seed(random_seed)
    env = simpy.Environment()
    loket = simpy.Resource(env, capacity=jumlah_loket)
    env.process(sumber_pelanggan(env, loket))
    env.process(monitor_antrean(env, loket))
    env.run(until=waktu_simulasi)

    return {
        "waktu_tunggu": data_waktu_tunggu,
        "waktu_sistem": data_waktu_sistem,
        "histori_waktu": histori_waktu,
        "histori_antrean": histori_panjang_antrean,
        "histori_sibuk": histori_server_sibuk,
    }

FA = "https://use.fontawesome.com/releases/v5.15.4/css/all.css"
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.FLATLY, FA])
app.title = "Simulasi Antrean Modern"

controls = dbc.Card(
    [
        dbc.CardHeader(html.H4("⚙️ Parameter Simulasi")),
        dbc.CardBody(
            [
                dbc.Row([
                    dbc.Col(dbc.Label("Jumlah Loket", html_for="slider-loket"), md=5),
                    dbc.Col(dcc.Slider(id='slider-loket', min=1, max=10, step=1, value=2, marks={i: str(i) for i in range(1, 11)}), md=7),
                ], align="center", className="mb-4"),
                dbc.Form([
                    dbc.Row([
                        dbc.Col(dbc.Label("Waktu Simulasi (menit)"), md=5),
                        dbc.Col(dbc.Input(id='input-sim-time', type='number', value=120, min=10, step=10), md=7),
                    ], className="mb-3"),
                    dbc.Row([
                        dbc.Col(dbc.Label("Rata-rata Kedatangan (menit)"), md=5),
                        dbc.Col(dbc.Input(id='input-arrival', type='number', value=2.0, min=0.1, step=0.1), md=7),
                    ], className="mb-3"),
                    dbc.Row([
                        dbc.Col(dbc.Label("Rata-rata Layanan (menit)"), md=5),
                        dbc.Col(dbc.Input(id='input-service', type='number', value=3.0, min=0.1, step=0.1), md=7),
                    ], className="mb-3"),
                ]),
                html.Div(
                    dbc.Button(
                        [html.I(className="fas fa-play me-2"), "Jalankan Simulasi"],
                        id="run-button", color="primary", n_clicks=0, className="w-100"
                    ),
                    className="d-grid gap-2 mt-4",
                )
            ]
        ),
    ],
    className="shadow"
)

initial_output = html.Div(
    dbc.Card(
        dbc.CardBody([
            html.H4("Selamat Datang!", className="card-title"),
            html.P("Silakan atur parameter di sebelah kiri dan klik 'Jalankan Simulasi' untuk melihat hasilnya di sini.", className="card-text"),
            html.P("Anda dapat menganalisis performa sistem antrean berdasarkan input yang Anda berikan."),
            html.Div(className="text-center mt-4", children=[
                html.I(className="fas fa-chart-line fa-4x text-light")
            ])
        ]),
        className="h-100"
    )
)

app.layout = dbc.Container(
    [
        html.Div(
            [
                html.H1("Dashboard Interaktif Simulasi Sistem Antrean", className="text-white"),
                html.P("Analisis Kinerja Sistem dengan SimPy dan Dash", className="text-white-50"),
            ],
            className="bg-primary p-4 mb-4 rounded shadow-sm text-center",
        ),
        dbc.Row(
            [
                dbc.Col(controls, md=4, className="mb-4"),
                dbc.Col(
                    dcc.Loading(
                        id="loading-output",
                        type="default",
                        children=html.Div(id="output-container", children=initial_output)
                    ),
                    md=8
                ),
            ],
            align="start",
        ),
    ],
    fluid=True,
    className="dbc"
)

def create_kpi_card(title, value, icon, color):
    return dbc.Card(
        dbc.CardBody([
            html.P(title, className="card-title text-muted mb-1"),
            html.H3(value, className=f"text-{color}"),
            html.I(className=f"fas {icon} fa-2x text-muted", style={'position': 'absolute', 'top': '20px', 'right': '20px'})
        ]),
        className="h-100 shadow-sm"
    )

@app.callback(
    Output("output-container", "children"),
    Input("run-button", "n_clicks"),
    [
        State("slider-loket", "value"),
        State("input-sim-time", "value"),
        State("input-arrival", "value"),
        State("input-service", "value"),
    ],
    prevent_initial_call=True
)
def update_dashboard(n_clicks, num_loket, sim_time, arrival_rate, service_rate):
    results = run_simulation(num_loket, sim_time, arrival_rate, service_rate, random_seed=n_clicks)

    if not results['waktu_tunggu']:
        avg_wait = max_wait = avg_system_time = total_pelanggan = 0
    else:
        avg_wait = np.mean(results['waktu_tunggu'])
        max_wait = np.max(results['waktu_tunggu'])
        avg_system_time = np.mean(results['waktu_sistem'])
        total_pelanggan = len(results['waktu_sistem'])

    max_queue = np.max(results['histori_antrean']) if results['histori_antrean'] else 0
    avg_utilization = (np.mean(results['histori_sibuk']) / num_loket * 100) if results['histori_sibuk'] else 0

    kpi_cards = dbc.Row([
        dbc.Col(create_kpi_card("Total Pelanggan", f"{total_pelanggan}", "fa-users", "primary"), md=4, className="mb-3"),
        dbc.Col(create_kpi_card("Utilisasi Rata-rata", f"{avg_utilization:.2f} %", "fa-cogs", "success"), md=4, className="mb-3"),
        dbc.Col(create_kpi_card("Antrean Terpanjang", f"{max_queue} orang", "fa-list-ol", "warning"), md=4, className="mb-3"),
    ])

    kpi_cards_waktu = dbc.Row([
        dbc.Col(create_kpi_card("Rata-rata Waktu Tunggu", f"{avg_wait:.2f} menit", "fa-hourglass-half", "info"), md=6, className="mb-3"),
        dbc.Col(create_kpi_card("Waktu Tunggu Maksimal", f"{max_wait:.2f} menit", "fa-stopwatch", "danger"), md=6, className="mb-3"),
    ])

    template = "plotly_white"
    
    fig_wait_time = go.Figure(go.Histogram(x=results['waktu_tunggu'], name='Waktu Tunggu', marker_color='#17a2b8'))
    fig_wait_time.add_vline(x=avg_wait, line_dash="dash", line_color="red", annotation_text=f"Rata-rata: {avg_wait:.2f}")
    fig_wait_time.update_layout(title_text="<b>Distribusi Waktu Tunggu Pelanggan</b>", xaxis_title="Waktu Tunggu (menit)", yaxis_title="Frekuensi", template=template)

    fig_queue_length = go.Figure(go.Scatter(x=results['histori_waktu'], y=results['histori_antrean'], mode='lines', line_shape='hv', fill='tozeroy', line_color='#ffc107'))
    fig_queue_length.update_layout(title_text="<b>Perkembangan Panjang Antrean vs Waktu</b>", xaxis_title="Waktu Simulasi (menit)", yaxis_title="Jumlah Pelanggan", template=template)

    output_layout = html.Div([
        kpi_cards,
        dbc.Tabs(
            [
                dbc.Tab(
                    dbc.Card(dbc.CardBody(dcc.Graph(figure=fig_queue_length))),
                    label="Analisis Antrean",
                    className="mt-3"
                ),
                dbc.Tab(
                    dbc.Card(dbc.CardBody([
                        dcc.Graph(figure=fig_wait_time),
                        html.Hr(),
                        kpi_cards_waktu
                    ])),
                    label="Analisis Waktu",
                    className="mt-3"
                ),
            ]
        )
    ])

    return output_layout

if __name__ == "__main__":
    app.run(debug=True)