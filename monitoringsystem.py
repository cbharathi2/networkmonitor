import subprocess
import ipaddress
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
import mysql.connector
import pandas as pd
import psutil
import time
import plotly.graph_objects as go
from dash import Dash, dcc, html
from dash.dependencies import Input, Output
import requests
import dash_bootstrap_components as dbc
import threading

# Initialize Dash app with Bootstrap
app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

# Initialize last valid sunburst chart figure
last_sunburst_figure = go.Figure()

# Function to check network connectivity
def check_network_connectivity():
    try:
        response = requests.get("https://www.google.com", timeout=1)
        return response.status_code == 200
    except requests.ConnectionError:
        return False

# Sunburst Chart Code
def ping(ip):
    """Ping an IP address to check if it's active."""
    result = subprocess.run(['ping', '-n', '1', '-w', '1', ip], stdout=subprocess.PIPE)
    return result.returncode == 0, ip

def convert_wildcard_to_cidr(wildcard_subnet):
    """Convert a wildcard subnet notation to CIDR notation."""
    if '*' in wildcard_subnet:
        base_ip = wildcard_subnet.replace('*', '0')
        return f'{base_ip}/24'
    return wildcard_subnet

def scan_subnet(subnet):
    """Scan a subnet and return the number of active IPs."""
    network = ipaddress.IPv4Network(subnet, strict=False)
    active_ips = []

    with ThreadPoolExecutor(max_workers=100) as executor:
        futures = [executor.submit(ping, str(ip)) for ip in network]
        for future in as_completed(futures):
            success, ip = future.result()
            if success:
                active_ips.append(ip)

    return len(active_ips)

def scan_subnets(subnets):
    """Scan multiple subnets and return results."""
    subnet_results = {}
    errors = []

    for subnet, department in subnets.items():
        cidr_subnet = convert_wildcard_to_cidr(subnet)
        try:
            active_device_count = scan_subnet(cidr_subnet)
            subnet_results[subnet] = (department, active_device_count)
        except Exception as e:
            errors.append(f"Error scanning {subnet}: {e}")

    total_active_devices = sum(count for _, count in subnet_results.values())
    last_refreshed = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return subnet_results, total_active_devices, last_refreshed, errors

def create_sunburst_chart(subnet_results, total_active_devices, last_refreshed, errors):
    """Create and return a sunburst chart."""
    labels = []
    parents = []
    values = []

    for subnet, (department, count) in subnet_results.items():
        labels.append(f"{subnet}\n({department})")
        parents.append("")
        values.append(count)

    fig = go.Figure(go.Sunburst(
        labels=labels,
        parents=parents,
        values=values,
        branchvalues="total",
        hoverinfo="label+value"
    ))

    fig.update_layout(
        title=f'Active Devices Count: {total_active_devices}',
        margin=dict(t=100, l=0, r=0, b=0),
        annotations=[
            dict(
                text=f"Last Refreshed: {last_refreshed}",
                xref='paper', yref='paper',
                x=0.5, y=1.1,
                showarrow=False,
                font=dict(size=12, color='gray'),
                align='center'
            )
        ],
    )

    return fig

GRAPH_UPDATE_INTERVAL = 2 * 60  # Update graph every 2 minutes (in seconds)
PAST_HOUR_DURATION = 2 * 60 * 60  # 2 hours in seconds

timestamps = []
sent_data = []
recv_data = []

def create_table():
    """Create the bandwidth_data table if it doesn't exist."""
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="bharathi",
        database="network_monitor"
    )
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bandwidth_data (
            id INT AUTO_INCREMENT PRIMARY KEY,
            timestamp DATETIME NOT NULL,
            bytes_sent BIGINT NOT NULL,
            bytes_recv BIGINT NOT NULL
        )
    """)
    conn.commit()
    cursor.close()
    conn.close()

def get_current_bandwidth():
    """Retrieve the current system bandwidth usage."""
    net_io_1 = psutil.net_io_counters()
    time.sleep(1)
    net_io_2 = psutil.net_io_counters()

    bytes_sent = net_io_2.bytes_sent - net_io_1.bytes_sent
    bytes_recv = net_io_2.bytes_recv - net_io_1.bytes_recv

    return bytes_sent, bytes_recv

def store_bandwidth_data(bytes_sent, bytes_recv):
    """Store the current bandwidth data in the database."""
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="bharathi",
        database="network_monitor"
    )
    cursor = conn.cursor()

    timestamp = datetime.now()
    query = """
        INSERT INTO bandwidth_data (timestamp, bytes_sent, bytes_recv) 
        VALUES (%s, %s, %s)
    """
    cursor.execute(query, (timestamp, bytes_sent, bytes_recv))
    conn.commit()
    cursor.close()
    conn.close()

    print(f"Stored data: {timestamp}, Sent: {bytes_sent}, Received: {bytes_recv}")

def fetch_data_from_database(start_time, end_time):
    """Fetch data from MySQL database within a specified time range."""
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="bharathi",
        database="network_monitor"
    )
    cursor = conn.cursor()

    query = """
        SELECT timestamp, bytes_sent, bytes_recv 
        FROM bandwidth_data 
        WHERE timestamp BETWEEN %s AND %s
        ORDER BY timestamp;
    """
    cursor.execute(query, (start_time, end_time))
    result = cursor.fetchall()

    cursor.close()
    conn.close()
    return result

def update_data():
    """Fetch the latest data and update global storage."""
    current_time = datetime.now()
    start_time = current_time - timedelta(seconds=PAST_HOUR_DURATION)
    end_time = current_time

    result = fetch_data_from_database(start_time, end_time)
    global timestamps, sent_data, recv_data

    if not result:
        print("No data fetched from the database.")
    else:
        df = pd.DataFrame(result, columns=['timestamp', 'bytes_sent', 'bytes_recv'])
        df['timestamp'] = pd.to_datetime(df['timestamp'])

        df['sent_mbps'] = (df['bytes_sent'] * 8) / (1024 * 1024)
        df['recv_mbps'] = (df['bytes_recv'] * 8) / (1024 * 1024)

        timestamps = df['timestamp'].tolist()
        sent_data = df['sent_mbps'].tolist()
        recv_data = df['recv_mbps'].tolist()

        print("Timestamps:", timestamps)
        print("Sent Data (Mbps):", sent_data)
        print("Received Data (Mbps):", recv_data)

# Define layout of Dash app with a modal for error message
app.layout = html.Div([
    html.Div([
        html.H1("Active Devices by Subnet", style={'text-align': 'center'}),
        dcc.Graph(id='live-update-graph'),  # Removed dcc.Loading
        dcc.Interval(
            id='interval-component-sunburst',
            interval=3 * 60 * 1000,  # 3 minutes in milliseconds
            n_intervals=0
        )
    ], style={'width': '48%', 'display': 'inline-block', 'vertical-align': 'top'}),

    html.Div([
        html.H1("Real-Time Network Bandwidth Monitoring"),
        dcc.Graph(id='live-bandwidth-graph'),
        dcc.Interval(
            id='interval-component-bandwidth',
            interval=GRAPH_UPDATE_INTERVAL * 1000,  # Convert seconds to milliseconds
            n_intervals=0
        )
    ], style={'width': '48%', 'display': 'inline-block', 'vertical-align': 'top'}),

    # Modal for network error message with only cross button
    dbc.Modal(
        [
            dbc.ModalHeader(dbc.ModalTitle("Network Error"), close_button=True),
            dbc.ModalBody("Error: Failed to retrieve active device data and bandwidth data. Please check the subnet scan configuration or network monitoring service."),
        ],
        id="network-error-modal",
        is_open=False,
        centered=True,
        backdrop=True,
    )
])

@app.callback(
    [Output('live-update-graph', 'figure'),
     Output('network-error-modal', 'is_open')],
    [Input('interval-component-sunburst', 'n_intervals')]
)
def update_sunburst_graph(sunburst_intervals):
    global last_sunburst_figure

    # Check network connectivity
    if not check_network_connectivity():
        return last_sunburst_figure, True  # Show modal

    # Update Sunburst Graph
    subnets = {
        '10.53.2.*': 'tele',
        '10.53.3.*': 'stores',
        '10.53.4.*': 'itc',
        '10.53.5.*': 'mechF',
        '10.53.6.*': 'pers',
        '10.53.7.*': 'MechS',
        '10.53.8.*': 'admin',
        '10.53.9.*': 'hosp',
        '10.53.10.*': 'accts',
        '10.53.11.*': 'engg',
        '10.53.12.*': 'dnd',
        '10.53.13.*': 'secur',
        '10.53.14.*': 'acctf',
        '10.53.15.*': 'mgmt',
        '10.53.16.*': 'mechss',
        '10.53.17.*': 'dslam',
        '10.53.18.*': 'chems',
        '10.53.19.*': 'elec',
        '10.53.20.*': 'actp'
    }

    def update_sunburst():
        return scan_subnets(subnets)

    with ThreadPoolExecutor() as executor:
        future = executor.submit(update_sunburst)
        subnet_results, total_active_devices, last_refreshed, errors = future.result()

    last_sunburst_figure = create_sunburst_chart(subnet_results, total_active_devices, last_refreshed, errors)
    return last_sunburst_figure, False  # Modal closed



@app.callback(
    Output('live-bandwidth-graph', 'figure'),
    [Input('interval-component-bandwidth', 'n_intervals')]
)
def update_bandwidth_graph(bandwidth_intervals):
    current_sent, current_recv = get_current_bandwidth()
    store_bandwidth_data(current_sent, current_recv)

    # Start the update data thread
    def update_bandwidth():
        update_data()

    bandwidth_thread = threading.Thread(target=update_bandwidth)
    bandwidth_thread.start()
    bandwidth_thread.join()  # Ensure update completes

    bandwidth_fig = go.Figure()
    bandwidth_fig.add_trace(go.Scatter(x=timestamps, y=sent_data, mode='lines+markers', name='Sent (Mbps)'))
    bandwidth_fig.add_trace(go.Scatter(x=timestamps, y=recv_data, mode='lines+markers', name='Received (Mbps)'))

    bandwidth_fig.update_layout(
        xaxis_title='Time',
        yaxis_title='Bandwidth (Mbps)',
        margin=dict(l=50, r=50, t=50, b=50),
    )

    return bandwidth_fig

if __name__ == '__main__':
    app.run_server(debug=True)

