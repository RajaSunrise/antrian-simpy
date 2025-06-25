import dash
from dash import dcc, html, Input, Output, State, no_update
import dash_bootstrap_components as dbc
import plotly.graph_objects as go

import simpy
import random
import numpy as np

# =============================================================================
# BAGIAN 1: FUNGSI SIMULASI SIMPY (DIBUAT SEBAGAI FUNGSI MANDIRI)
# =============================================================================

def run_simulation(jumlah_loket, waktu_simulasi, rata_kedatangan, rata_layanan, random_seed):
    """
    Menjalankan simulasi antrean SimPy dengan parameter yang diberikan
    dan mengembalikan data hasil simulasi.
    """
    # --- Variabel untuk Pengumpulan Data ---
    data_waktu_tunggu = []
    data_waktu_sistem = []
    histori_panjang_antrean = []
    histori_waktu = []
    histori_server_sibuk = []

    # Inner function untuk proses simulasi
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
            yield env.timeout(1.0) # Monitor setiap 1 satuan waktu

    # --- Setup dan Menjalankan Simulasi ---
    random.seed(random_seed)
    env = simpy.Environment()
    loket = simpy.Resource(env, capacity=jumlah_loket)
    env.process(sumber_pelanggan(env, loket))
    env.process(monitor_antrean(env, loket))
    env.run(until=waktu_simulasi)

    # Mengembalikan semua data yang dikumpulkan dalam sebuah dictionary
    return {
        "waktu_tunggu": data_waktu_tunggu,
        "waktu_sistem": data_waktu_sistem,
        "histori_waktu": histori_waktu,
        "histori_antrean": histori_panjang_antrean,
        "histori_sibuk": histori_server_sibuk,
    }


# =============================================================================
# BAGIAN 2: SETUP APLIKASI DASH
# =============================================================================

# Gunakan tema Bootstrap yang modern dan bersih (LUX adalah pilihan yang bagus)
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.LUX])
app.title = "Simulasi Antrean"

# --- Layout Panel Kontrol ---
controls = dbc.Card(
    [
        dbc.CardHeader(html.H4("Parameter Simulasi")),
        dbc.CardBody(
            [
                dbc.Row([
                    dbc.Col(dbc.Label("Jumlah Loket:"), width=6),
                    dbc.Col(dcc.Slider(id='slider-loket', min=1, max=10, step=1, value=2, marks={i: str(i) for i in range(1, 11)}), width=6),
                ], align="center", className="mb-3"),

                dbc.Row([
                    dbc.Col(dbc.Label("Waktu Simulasi (menit):"), width=6),
                    dbc.Col(dcc.Input(id='input-sim-time', type='number', value=120, min=10, step=10), width=6),
                ], align="center", className="mb-3"),

                dbc.Row([
                    dbc.Col(dbc.Label("Rata-rata Kedatangan (menit):"), width=6),
                    dbc.Col(dcc.Input(id='input-arrival', type='number', value=2.0, min=0.1, step=0.1), width=6),
                ], align="center", className="mb-3"),

                dbc.Row([
                    dbc.Col(dbc.Label("Rata-rata Layanan (menit):"), width=6),
                    dbc.Col(dcc.Input(id='input-service', type='number', value=3.0, min=0.1, step=0.1), width=6),
                ], align="center", className="mb-3"),

                html.Div(
                    dbc.Button("Jalankan Simulasi", id="run-button", color="primary", n_clicks=0, className="w-100"),
                    className="d-grid gap-2",
                )
            ]
        ),
    ]
)

# --- Layout Aplikasi Utama ---
app.layout = dbc.Container(
    [
        html.H1("Dashboard Simulasi Sistem Antrean", className="text-center my-4"),
        html.Hr(),
        dbc.Row(
            [
                # Kolom kiri untuk panel kontrol
                dbc.Col(controls, md=4),

                # Kolom kanan untuk output (grafik dan statistik)
                dbc.Col(
                    dcc.Loading(
                        id="loading-output",
                        type="default",
                        children=[
                            html.Div(id="output-container")
                        ]
                    ), md=8
                ),
            ],
            align="start",
        ),
    ],
    fluid=True,
)


# =============================================================================
# BAGIAN 3: CALLBACK UNTUK INTERAKTIVITAS
# =============================================================================

@app.callback(
    Output("output-container", "children"),
    Input("run-button", "n_clicks"),
    [
        State("slider-loket", "value"),
        State("input-sim-time", "value"),
        State("input-arrival", "value"),
        State("input-service", "value"),
    ],
    prevent_initial_call=True # Mencegah callback berjalan saat aplikasi pertama kali dimuat
)
def update_dashboard(n_clicks, num_loket, sim_time, arrival_rate, service_rate):
    # Jalankan simulasi dengan parameter dari GUI
    results = run_simulation(num_loket, sim_time, arrival_rate, service_rate, random_seed=n_clicks)

    # --- Buat Grafik-grafik ---

    # 1. Grafik Distribusi Waktu Tunggu
    fig_wait_time = go.Figure()
    if results['waktu_tunggu']:
        fig_wait_time.add_trace(go.Histogram(x=results['waktu_tunggu'], name='Waktu Tunggu', marker_color='#3498db'))
        avg_wait = np.mean(results['waktu_tunggu'])
        fig_wait_time.add_vline(x=avg_wait, line_dash="dash", line_color="red", annotation_text=f"Rata-rata: {avg_wait:.2f}")
    fig_wait_time.update_layout(title_text="<b>Distribusi Waktu Tunggu Pelanggan</b>", xaxis_title="Waktu Tunggu (menit)", yaxis_title="Frekuensi", template="plotly_white")

    # 2. Grafik Perkembangan Panjang Antrean
    fig_queue_length = go.Figure()
    fig_queue_length.add_trace(go.Scatter(x=results['histori_waktu'], y=results['histori_antrean'], mode='lines', line_shape='hv', fill='tozeroy', line_color='#e74c3c'))
    fig_queue_length.update_layout(title_text="<b>Perkembangan Panjang Antrean</b>", xaxis_title="Waktu Simulasi (menit)", yaxis_title="Jumlah Pelanggan", template="plotly_white")

    # 3. Grafik Utilisasi Loket
    fig_server_util = go.Figure()
    fig_server_util.add_trace(go.Scatter(x=results['histori_waktu'], y=results['histori_sibuk'], mode='lines', line_shape='hv', fill='tozeroy', line_color='#2ecc71'))
    fig_server_util.update_layout(title_text="<b>Jumlah Loket Sibuk</b>", xaxis_title="Waktu Simulasi (menit)", yaxis_title="Jumlah Loket", template="plotly_white", yaxis=dict(tickmode='linear', tick0=0, dtick=1))

    # --- Siapkan Teks Ringkasan Statistik ---
    if not results['waktu_tunggu']: # Jika tidak ada pelanggan yang dilayani
        avg_wait = 0
        max_wait = 0
        avg_system_time = 0
    else:
        avg_wait = np.mean(results['waktu_tunggu'])
        max_wait = np.max(results['waktu_tunggu'])
        avg_system_time = np.mean(results['waktu_sistem'])

    total_pelanggan = len(results['waktu_sistem'])
    max_queue = np.max(results['histori_antrean']) if results['histori_antrean'] else 0
    avg_utilization = (np.mean(results['histori_sibuk']) / num_loket * 100) if results['histori_sibuk'] else 0

    summary_card = dbc.Card(
        dbc.CardBody([
            html.H4("Ringkasan Statistik", className="card-title"),
            html.P(f"Total Pelanggan Dilayani: {total_pelanggan}"),
            html.P(f"Rata-rata Waktu Tunggu: {avg_wait:.2f} menit"),
            html.P(f"Waktu Tunggu Maksimal: {max_wait:.2f} menit"),
            html.P(f"Rata-rata Waktu di Sistem: {avg_system_time:.2f} menit"),
            html.P(f"Antrean Terpanjang: {max_queue} orang"),
            html.P(f"Utilisasi Rata-rata Loket: {avg_utilization:.2f} %"),
        ])
    )

    # --- Gabungkan semua elemen output menjadi satu layout ---
    return html.Div([
        dbc.Row([
            dbc.Col(dbc.Card(dcc.Graph(figure=fig_wait_time)), md=6, className="mb-4"),
            dbc.Col(dbc.Card(dcc.Graph(figure=fig_queue_length)), md=6, className="mb-4"),
        ]),
        dbc.Row([
            dbc.Col(dbc.Card(dcc.Graph(figure=fig_server_util)), md=6, className="mb-4"),
            dbc.Col(summary_card, md=6, className="mb-4"),
        ]),
    ])


# =============================================================================
# BAGIAN 4: MENJALANKAN SERVER APLIKASI
# =============================================================================
if __name__ == "__main__":
    # PERUBAHAN DI SINI: ganti app.run_server menjadi app.run
    app.run(debug=True)
